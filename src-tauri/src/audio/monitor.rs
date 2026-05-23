use std::{
    collections::HashMap,
    sync::{
        atomic::{AtomicBool, Ordering},
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

    /// Force-restart monitoring for one channel immediately, regardless of
    /// whether the config looks different from the last known value.
    pub fn restart_channel(&mut self, cfg: ChannelConfig, app: tauri::AppHandle) {
        if let Some(entry) = self.channels.get_mut(&cfg.id) {
            entry.last_config = cfg.clone();
            let _ = entry.config_tx.try_send(cfg);
        } else {
            self.upsert(cfg, app);
        }
    }

    fn upsert(&mut self, cfg: ChannelConfig, app: tauri::AppHandle) {
        let ch_id = cfg.id.clone();

        if let Some(entry) = self.channels.get_mut(&ch_id) {
            let changed = cfg.direction != entry.last_config.direction
                || cfg.device   != entry.last_config.device
                || cfg.enabled  != entry.last_config.enabled;
            if changed {
                entry.last_config = cfg.clone();
                let _ = entry.config_tx.try_send(cfg);
            }
        } else {
            let (tx, rx) = crossbeam_channel::bounded::<ChannelConfig>(8);
            let stop      = Arc::new(AtomicBool::new(false));
            let stop_loop = Arc::clone(&stop);
            let id        = ch_id.clone();
            let _ = tx.try_send(cfg.clone());
            std::thread::spawn(move || channel_monitor_loop(id, rx, stop_loop, app));
            self.channels.insert(ch_id, ChannelEntry { config_tx: tx, stop, last_config: cfg });
        }
    }

    pub fn stop(&mut self) {
        for (_, entry) in self.channels.drain() {
            entry.stop.store(true, Ordering::SeqCst);
        }
    }
}

fn should_monitor(direction: &str) -> bool {
    matches!(direction, "OUT" | "APP" | "MICOUT")
}

/// Long-running per-channel loop — never exits unless the stop flag is set.
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
                Ok(samples) => {
                    got_audio = true;
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
                        retry_wait(&config_rx, &mut current, &stop);
                        break 'meter;
                    }
                }
                Err(RecvTimeoutError::Disconnected) => {
                    // Capture thread exited (device error, disconnected, etc) — retry.
                    let _ = app.emit("channel-level",
                        serde_json::json!({ "id": ch_id, "level": 0.0 }));
                    retry_wait(&config_rx, &mut current, &stop);
                    break 'meter;
                }
            }
        }
    }

    broadcast_level(&app, &ch_id, 0.0);
}

/// Wait up to 2 s between retries; returns early on config change or stop.
fn retry_wait(
    config_rx: &crossbeam_channel::Receiver<ChannelConfig>,
    current:   &mut ChannelConfig,
    stop:      &Arc<AtomicBool>,
) {
    let deadline = Instant::now() + Duration::from_secs(2);
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
