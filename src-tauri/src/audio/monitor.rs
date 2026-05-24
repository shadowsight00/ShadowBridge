use std::{
    collections::HashMap,
    sync::{
        atomic::{AtomicBool, AtomicU32, Ordering},
        Arc,
    },
    time::{Duration, Instant},
};

use crossbeam_channel::RecvTimeoutError;
use tauri::Emitter;

use crate::config::ChannelConfig;
use super::capture::{app_loopback_capture_thread, loopback_capture_thread, mic_capture_thread};
use super::meter::LevelMeter;

struct ChannelEntry {
    config_tx:   crossbeam_channel::Sender<ChannelConfig>,
    stop:        Arc<AtomicBool>,
    last_config: ChannelConfig,
    vol:         Arc<AtomicU32>, // live volume shared with set_volume()
}

pub struct MonitoringEngine {
    channels: HashMap<String, ChannelEntry>,
}

impl MonitoringEngine {
    pub fn new() -> Self {
        Self { channels: HashMap::new() }
    }

    /// Start or update monitoring for all supplied channels.
    /// Channels no longer in the list have their loops stopped.
    pub fn start(&mut self, channels: Vec<ChannelConfig>, app: tauri::AppHandle) {
        let new_ids: std::collections::HashSet<String> =
            channels.iter().map(|c| c.id.clone()).collect();

        self.channels.retain(|id, entry| {
            if new_ids.contains(id) {
                true
            } else {
                entry.stop.store(true, Ordering::SeqCst);
                false
            }
        });

        for ch in channels {
            self.upsert(ch, app.clone());
        }
    }

    /// Force-restart monitoring for one channel immediately.
    pub fn restart_channel(&mut self, cfg: ChannelConfig, app: tauri::AppHandle) {
        if let Some(entry) = self.channels.get_mut(&cfg.id) {
            // Sync vol so the meter reflects any volume baked into this config.
            entry.vol.store(vol_raw(cfg.volume), Ordering::Relaxed);
            entry.last_config = cfg.clone();
            let _ = entry.config_tx.try_send(cfg);
        } else {
            self.upsert(cfg, app);
        }
    }

    /// Update the live volume for a channel (called from set_channel_volume).
    /// `vol_frac` is 0.0–1.0 (same scale as AudioEngine::set_volume).
    pub fn set_volume(&self, channel_id: &str, vol_frac: f32) {
        if let Some(entry) = self.channels.get(channel_id) {
            entry.vol.store((vol_frac.clamp(0.0, 1.0) * 10_000.0) as u32, Ordering::Relaxed);
        }
    }

    fn upsert(&mut self, cfg: ChannelConfig, app: tauri::AppHandle) {
        let ch_id = cfg.id.clone();

        if let Some(entry) = self.channels.get_mut(&ch_id) {
            // Always sync the live volume even if nothing else changed.
            entry.vol.store(vol_raw(cfg.volume), Ordering::Relaxed);

            let changed = cfg.direction != entry.last_config.direction
                || cfg.device   != entry.last_config.device
                || cfg.enabled  != entry.last_config.enabled;
            if changed {
                entry.last_config = cfg.clone();
                let _ = entry.config_tx.try_send(cfg);
            } else {
                entry.last_config = cfg;
            }
        } else {
            let vol       = Arc::new(AtomicU32::new(vol_raw(cfg.volume)));
            let vol_clone = Arc::clone(&vol);
            let (tx, rx)  = crossbeam_channel::bounded::<ChannelConfig>(8);
            let stop      = Arc::new(AtomicBool::new(false));
            let stop_loop = Arc::clone(&stop);
            let id        = ch_id.clone();
            let _ = tx.try_send(cfg.clone());
            std::thread::spawn(move || channel_monitor_loop(id, rx, stop_loop, app, vol_clone));
            self.channels.insert(ch_id, ChannelEntry { config_tx: tx, stop, last_config: cfg, vol });
        }
    }

    pub fn stop(&mut self) {
        for (_, entry) in self.channels.drain() {
            entry.stop.store(true, Ordering::SeqCst);
        }
    }
}

/// Convert a 0–100 config volume to the AtomicU32 storage format (0–10 000).
fn vol_raw(volume: u32) -> u32 {
    (volume as f32 / 100.0 * 10_000.0) as u32
}

fn should_monitor(direction: &str) -> bool {
    matches!(direction, "OUT" | "APP" | "MICOUT")
}

fn broadcast_level(app: &tauri::AppHandle, ch_id: &str, level: f32) {
    use tauri::{Emitter, Manager};
    let _ = app.emit("channel-level", serde_json::json!({ "id": ch_id, "level": level }));
    let state = app.state::<crate::state::AppState>();
    crate::websocket::broadcast(
        &state.ws_clients,
        serde_json::json!({"event": "channel_level", "id": ch_id, "level": level}).to_string(),
    );
}

fn channel_monitor_loop(
    ch_id:     String,
    config_rx: crossbeam_channel::Receiver<ChannelConfig>,
    stop:      Arc<AtomicBool>,
    app:       tauri::AppHandle,
    vol:       Arc<AtomicU32>,
) {
    // Wait for the initial config before doing anything.
    let mut current: ChannelConfig = loop {
        if stop.load(Ordering::SeqCst) { return; }
        match config_rx.recv_timeout(Duration::from_millis(200)) {
            Ok(cfg) => break cfg,
            Err(_)  => continue,
        }
    };

    'outer: loop {
        if stop.load(Ordering::SeqCst) { break; }

        // Drain any queued config updates (take the latest one).
        while let Ok(cfg) = config_rx.try_recv() {
            current = cfg;
        }

        // If this channel type cannot produce local audio, idle until config changes.
        if !current.enabled || current.device.is_empty() || !should_monitor(&current.direction) {
            broadcast_level(&app, &ch_id, 0.0);
            loop {
                if stop.load(Ordering::SeqCst) { break 'outer; }
                if let Ok(cfg) = config_rx.recv_timeout(Duration::from_millis(200)) {
                    current = cfg;
                    break;
                }
            }
            continue;
        }

        // Spawn the appropriate capture thread.
        let (audio_tx, audio_rx) = crossbeam_channel::bounded::<Vec<f32>>(32);
        let inner_stop  = Arc::new(AtomicBool::new(false));
        let cap_stop    = Arc::clone(&inner_stop);
        let dev         = current.device.clone();
        let app_cap     = app.clone();

        match current.direction.as_str() {
            "OUT" => {
                std::thread::spawn(move || {
                    let _ = loopback_capture_thread(dev, audio_tx, cap_stop, app_cap);
                });
            }
            "APP" => {
                std::thread::spawn(move || {
                    let _ = app_loopback_capture_thread(dev, audio_tx, cap_stop, app_cap);
                });
            }
            "MICOUT" => {
                std::thread::spawn(move || {
                    let _ = mic_capture_thread(dev, audio_tx, cap_stop, app_cap);
                });
            }
            _ => unreachable!(),
        }

        // Meter until the capture thread dies, a config change arrives, or stop.
        let mut meter     = LevelMeter::new(4800);
        let mut last_emit = Instant::now();
        let open_time     = Instant::now();
        let mut got_audio = false;

        'meter: loop {
            if stop.load(Ordering::SeqCst) {
                inner_stop.store(true, Ordering::SeqCst);
                break 'outer;
            }

            if let Ok(cfg) = config_rx.try_recv() {
                current = cfg;
                inner_stop.store(true, Ordering::SeqCst);
                break 'meter; // Restart with updated config immediately.
            }

            match audio_rx.recv_timeout(Duration::from_millis(50)) {
                Ok(mut samples) => {
                    got_audio = true;
                    // Read the live volume (updated by set_volume() on every fader move).
                    let vol_frac   = vol.load(Ordering::Relaxed) as f32 / 10_000.0;
                    let multiplier = super::vol_to_multiplier(vol_frac);
                    for s in samples.iter_mut() { *s *= multiplier; }
                    meter.push(&samples);
                    if last_emit.elapsed() >= Duration::from_millis(60) {
                        broadcast_level(&app, &ch_id, meter.level());
                        last_emit = Instant::now();
                    }
                }
                Err(RecvTimeoutError::Timeout) => {
                    // No audio after 2 s — device probably unavailable; retry silently.
                    if !got_audio && open_time.elapsed() > Duration::from_secs(2) {
                        inner_stop.store(true, Ordering::SeqCst);
                        let _ = app.emit("channel-level",
                            serde_json::json!({ "id": ch_id, "level": 0.0 }));
                        let dir = current.direction.clone();
                        retry_wait(&config_rx, &mut current, &stop, &dir);
                        break 'meter;
                    }
                }
                Err(RecvTimeoutError::Disconnected) => {
                    // Capture thread exited (device error, disconnected, etc) — retry.
                    let _ = app.emit("channel-level",
                        serde_json::json!({ "id": ch_id, "level": 0.0 }));
                    let dir = current.direction.clone();
                    retry_wait(&config_rx, &mut current, &stop, &dir);
                    break 'meter;
                }
            }
        }
    }

    broadcast_level(&app, &ch_id, 0.0);
}

/// Wait between retries; returns early on config change or stop.
/// MICOUT reconnects faster (1 s) so mic audio returns quickly after a CPU spike.
fn retry_wait(
    config_rx: &crossbeam_channel::Receiver<ChannelConfig>,
    current:   &mut ChannelConfig,
    stop:      &Arc<AtomicBool>,
    direction: &str,
) {
    let wait_secs = if direction == "MICOUT" { 1 } else { 2 };
    let deadline = Instant::now() + Duration::from_secs(wait_secs);
    loop {
        if stop.load(Ordering::SeqCst) { return; }
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() { return; }
        let wait = remaining.min(Duration::from_millis(100));
        if let Ok(cfg) = config_rx.recv_timeout(wait) {
            *current = cfg;
            return;
        }
    }
}
