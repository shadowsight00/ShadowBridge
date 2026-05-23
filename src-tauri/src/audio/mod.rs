mod capture;
pub mod meter;
mod monitor;
mod playback;
pub mod stream;

pub use monitor::MonitoringEngine;

use std::{
    collections::HashMap,
    sync::{
        atomic::{AtomicBool, AtomicU32, Ordering},
        Arc,
    },
    time::{Duration, Instant},
};

use cpal::{traits::{DeviceTrait, HostTrait}, BufferSize, SampleRate, StreamConfig};
use crossbeam_channel::RecvTimeoutError;
use tauri::Emitter;

use crate::config::ChannelConfig;
use capture::{app_loopback_capture_thread, loopback_capture_thread, mic_capture_thread};
use meter::LevelMeter;
use playback::PlaybackStream;

const WIRE_CHANNELS: u16 = 2;

struct EngineChannel {
    stop:     Arc<AtomicBool>,
    vol:      Arc<AtomicU32>,
    playback: Option<PlaybackStream>, // owned by channel; drop = stop cpal stream
}

pub struct AudioEngine {
    running:          bool,
    channels:         HashMap<String, EngineChannel>,
    dest_ip:          String,
    sample_rate:      u32,
    buffer_size:      u32,
    buffer_offset_ms: u32,
}

impl AudioEngine {
    pub fn new() -> Self {
        Self {
            running:          false,
            channels:         HashMap::new(),
            dest_ip:          String::new(),
            sample_rate:      48000,
            buffer_size:      1024,
            buffer_offset_ms: 20,
        }
    }

    pub fn start(
        &mut self,
        channels:         Vec<ChannelConfig>,
        dest_ip:          &str,
        _mode:            &str,
        app:              tauri::AppHandle,
        sample_rate:      u32,
        buffer_size:      u32,
        buffer_offset_ms: u32,
    ) -> anyhow::Result<()> {
        if self.running { return Ok(()); }
        self.dest_ip          = dest_ip.to_string();
        self.sample_rate      = sample_rate;
        self.buffer_size      = buffer_size;
        self.buffer_offset_ms = buffer_offset_ms;
        let count = channels.len();
        for ch in channels {
            self.start_one_channel(ch, &app);
        }
        self.running = true;
        log::info!("AudioEngine: started {count} channel(s)");
        Ok(())
    }

    /// Hot-swap one channel without touching others.
    pub fn restart_channel(&mut self, ch: ChannelConfig, app: tauri::AppHandle) {
        self.stop_one_channel(&ch.id);
        self.start_one_channel(ch, &app);
    }

    pub fn set_volume(&self, channel_id: &str, volume: f32) {
        if let Some(entry) = self.channels.get(channel_id) {
            entry.vol.store((volume.clamp(0.0, 1.0) * 10_000.0) as u32, Ordering::Relaxed);
        }
    }

    pub fn stop(&mut self) {
        for (_, entry) in self.channels.drain() {
            entry.stop.store(true, Ordering::SeqCst);
            // Dropping entry drops PlaybackStream → cpal stream stops.
        }
        self.running = false;
        log::info!("AudioEngine: stopped");
    }

    pub fn is_running(&self) -> bool { self.running }

    fn stop_one_channel(&mut self, id: &str) {
        if let Some(entry) = self.channels.remove(id) {
            entry.stop.store(true, Ordering::SeqCst);
            // entry.playback dropped here
        }
    }

    fn start_one_channel(&mut self, ch: ChannelConfig, app: &tauri::AppHandle) {
        if !ch.enabled { return; }

        let stop    = Arc::new(AtomicBool::new(false));
        let vol     = Arc::new(AtomicU32::new((ch.volume as f32 / 100.0 * 10_000.0) as u32));
        let mut playback = None;

        let _ = app.emit("engine-log", serde_json::json!({
            "message": format!("Channel '{}' ({}) starting — port {}", ch.name, ch.direction, ch.port)
        }));

        match ch.direction.as_str() {
            "OUT" => {
                if ch.device.is_empty() {
                    let _ = app.emit("engine-log", serde_json::json!({
                        "message": format!("Channel '{}' skipped — no device set", ch.name)
                    }));
                    return;
                }
                let (tx, rx)  = crossbeam_channel::bounded::<Vec<f32>>(32);
                let stop_cap  = Arc::clone(&stop);
                let name      = ch.name.clone();
                let dev_name  = ch.device.clone();
                let app_cap   = app.clone();
                std::thread::spawn(move || {
                    if let Err(e) = loopback_capture_thread(dev_name, tx, stop_cap.clone(), app_cap.clone()) {
                        if !stop_cap.load(Ordering::SeqCst) {
                            log::error!("[{name}] loopback exited: {e}");
                            let _ = app_cap.emit("engine-error", serde_json::json!({
                                "message": format!("Capture failed [{name}]: {e}")
                            }));
                        }
                    }
                });
                let dest = format!("{}:{}", self.dest_ip, ch.port);
                let app_c = app.clone(); let ch_id = ch.id.clone(); let ch_name = ch.name.clone();
                let vol2 = Arc::clone(&vol); let stop2 = Arc::clone(&stop);
                std::thread::spawn(move || { sender_thread(ch_id, ch_name, rx, dest, vol2, stop2, app_c); });
            }

            "APP" => {
                if ch.device.is_empty() {
                    let _ = app.emit("engine-log", serde_json::json!({
                        "message": format!("Channel '{}' skipped — no app selected", ch.name)
                    }));
                    return;
                }
                let (tx, rx)  = crossbeam_channel::bounded::<Vec<f32>>(32);
                let stop_cap  = Arc::clone(&stop);
                let name      = ch.name.clone();
                let proc_name = ch.device.clone();
                let app_cap   = app.clone();
                std::thread::spawn(move || {
                    if let Err(e) = app_loopback_capture_thread(proc_name, tx, stop_cap.clone(), app_cap.clone()) {
                        if !stop_cap.load(Ordering::SeqCst) {
                            log::error!("[{name}] app loopback exited: {e}");
                            let _ = app_cap.emit("engine-error", serde_json::json!({
                                "message": format!("App capture failed [{name}]: {e}")
                            }));
                        }
                    }
                });
                let dest = format!("{}:{}", self.dest_ip, ch.port);
                let app_c = app.clone(); let ch_id = ch.id.clone(); let ch_name = ch.name.clone();
                let vol2 = Arc::clone(&vol); let stop2 = Arc::clone(&stop);
                std::thread::spawn(move || { sender_thread(ch_id, ch_name, rx, dest, vol2, stop2, app_c); });
            }

            "MICOUT" => {
                if ch.device.is_empty() {
                    let _ = app.emit("engine-log", serde_json::json!({
                        "message": format!("Channel '{}' skipped — no device set", ch.name)
                    }));
                    return;
                }
                let (tx, rx)  = crossbeam_channel::bounded::<Vec<f32>>(32);
                let stop_cap  = Arc::clone(&stop);
                let name      = ch.name.clone();
                let dev_name  = ch.device.clone();
                let app_cap   = app.clone();
                std::thread::spawn(move || {
                    if let Err(e) = mic_capture_thread(dev_name, tx, stop_cap.clone(), app_cap.clone()) {
                        if !stop_cap.load(Ordering::SeqCst) {
                            log::error!("[{name}] mic capture exited: {e}");
                            let _ = app_cap.emit("engine-error", serde_json::json!({
                                "message": format!("Mic capture failed [{name}]: {e}")
                            }));
                        }
                    }
                });
                let dest = format!("{}:{}", self.dest_ip, ch.port);
                let app_c = app.clone(); let ch_id = ch.id.clone(); let ch_name = ch.name.clone();
                let vol2 = Arc::clone(&vol); let stop2 = Arc::clone(&stop);
                std::thread::spawn(move || { sender_thread(ch_id, ch_name, rx, dest, vol2, stop2, app_c); });
            }

            "IN" | "MIC" => {
                if ch.device.is_empty() {
                    let _ = app.emit("engine-log", serde_json::json!({
                        "message": format!("Channel '{}' skipped — no output device set", ch.name)
                    }));
                    return;
                }
                let host   = cpal::default_host();
                let device = match find_output_device(&host, &ch.device) {
                    Some(d) => d,
                    None => {
                        let _ = app.emit("engine-error", serde_json::json!({
                            "message": format!("Channel '{}': output device '{}' not found", ch.name, ch.device)
                        }));
                        return;
                    }
                };
                let prebuffer = (self.buffer_offset_ms as usize * self.sample_rate as usize / 1000) * 2;
                let cfg = preferred_config(&device.default_output_config(), &ch.name, self.sample_rate, self.buffer_size, false);
                let (ptx, prx) = crossbeam_channel::bounded::<Vec<f32>>(64);
                match PlaybackStream::new(&device, &cfg, prx, prebuffer) {
                    Ok(s)  => { playback = Some(s); }
                    Err(e) => { log::error!("[{}] playback: {e}", ch.name); return; }
                }
                let bind_addr = format!("0.0.0.0:{}", ch.port);
                let app_c = app.clone(); let ch_id = ch.id.clone(); let ch_name = ch.name.clone();
                let vol2 = Arc::clone(&vol); let stop2 = Arc::clone(&stop);
                std::thread::spawn(move || { receiver_thread(ch_id, ch_name, bind_addr, vol2, stop2, app_c, ptx); });
            }

            other => { log::warn!("unknown direction '{other}' for channel '{}'", ch.name); return; }
        }

        self.channels.insert(ch.id, EngineChannel { stop, vol, playback });
    }
}

// ── Config helpers ────────────────────────────────────────────────────────────

fn preferred_config(
    default: &Result<cpal::SupportedStreamConfig, cpal::DefaultStreamConfigError>,
    name:        &str,
    rate:        u32,
    buf_size:    u32,
    is_input:    bool,
) -> StreamConfig {
    let kind = if is_input { "input" } else { "output" };
    match default {
        Ok(def) if def.sample_rate().0 != rate || def.channels() != WIRE_CHANNELS => {
            log::info!("[{name}] {kind} native {}Hz×{}ch → requesting {rate}Hz×{WIRE_CHANNELS}ch",
                def.sample_rate().0, def.channels());
            StreamConfig {
                sample_rate: SampleRate(rate),
                channels:    WIRE_CHANNELS,
                buffer_size: BufferSize::Fixed(buf_size),
            }
        }
        Ok(def) => {
            let mut c: StreamConfig = def.clone().into();
            c.buffer_size = BufferSize::Fixed(buf_size);
            c
        }
        Err(e) => {
            log::warn!("[{name}] {kind} config error ({e}), using defaults");
            StreamConfig {
                sample_rate: SampleRate(rate),
                channels:    WIRE_CHANNELS,
                buffer_size: BufferSize::Fixed(buf_size),
            }
        }
    }
}

fn find_input_device(host: &cpal::Host, name: &str) -> Option<cpal::Device> {
    if name.is_empty() { return host.default_input_device(); }
    host.input_devices().ok()
        .and_then(|mut it| it.find(|d| d.name().ok().as_deref() == Some(name)))
        .or_else(|| host.default_input_device())
}

fn find_output_device(host: &cpal::Host, name: &str) -> Option<cpal::Device> {
    if name.is_empty() { return None; }
    host.output_devices().ok()
        .and_then(|mut it| it.find(|d| d.name().ok().as_deref() == Some(name)))
}

// ── Per-channel threads ───────────────────────────────────────────────────────

fn sender_thread(
    ch_id:   String,
    ch_name: String,
    rx:      crossbeam_channel::Receiver<Vec<f32>>,
    dest:    String,
    vol:     Arc<AtomicU32>,
    stop:    Arc<AtomicBool>,
    app:     tauri::AppHandle,
) {
    use tauri::Manager;
    let ws = app.state::<crate::state::AppState>().ws_clients.clone();

    let socket = match std::net::UdpSocket::bind("0.0.0.0:0") {
        Ok(s)  => s,
        Err(e) => {
            let _ = app.emit("engine-error", serde_json::json!({ "message": format!("'{ch_name}' UDP bind failed: {e}") }));
            return;
        }
    };
    if let Err(e) = socket.connect(&dest) {
        let _ = app.emit("engine-error", serde_json::json!({ "message": format!("'{ch_name}' UDP connect {dest} failed: {e}") }));
        return;
    }
    let _ = app.emit("engine-log", serde_json::json!({ "message": format!("SEND '{ch_name}' → {dest}") }));
    let _ = app.emit("channel-status", serde_json::json!({ "id": ch_id, "status": "active" }));
    crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_status","id":ch_id,"status":"active"}).to_string());

    let mut meter     = LevelMeter::new(4800);
    let mut last_emit = Instant::now();
    const  EMIT_MS:  Duration = Duration::from_millis(80);

    loop {
        if stop.load(Ordering::SeqCst) { break; }
        match rx.recv_timeout(Duration::from_millis(50)) {
            Ok(mut samples) => {
                let volume = vol.load(Ordering::Relaxed) as f32 / 10_000.0;
                if volume != 1.0 { for s in &mut samples { *s *= volume; } }
                meter.push(&samples);

                let bytes: Vec<u8> = samples.iter().flat_map(|s| s.to_le_bytes()).collect();
                if let Err(e) = socket.send(&bytes) { log::warn!("[{ch_id}] UDP send: {e}"); }

                if last_emit.elapsed() >= EMIT_MS {
                    let level = meter.level();
                    let _ = app.emit("channel-level", serde_json::json!({ "id": ch_id, "level": level }));
                    crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_level","id":ch_id,"level":level}).to_string());
                    last_emit = Instant::now();
                }
            }
            Err(RecvTimeoutError::Timeout)      => continue,
            Err(RecvTimeoutError::Disconnected) => break,
        }
    }
    let _ = app.emit("channel-level", serde_json::json!({ "id": ch_id, "level": 0.0 }));
    crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_level","id":ch_id,"level":0.0}).to_string());
    if !stop.load(Ordering::SeqCst) {
        let _ = app.emit("channel-status", serde_json::json!({ "id": ch_id, "status": "idle" }));
        crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_status","id":ch_id,"status":"idle"}).to_string());
    }
}

fn receiver_thread(
    ch_id:     String,
    ch_name:   String,
    bind_addr: String,
    vol:       Arc<AtomicU32>,
    stop:      Arc<AtomicBool>,
    app:       tauri::AppHandle,
    tx:        crossbeam_channel::Sender<Vec<f32>>,
) {
    use tauri::Manager;
    let ws = app.state::<crate::state::AppState>().ws_clients.clone();

    let socket = match std::net::UdpSocket::bind(&bind_addr) {
        Ok(s)  => s,
        Err(e) => {
            let _ = app.emit("engine-error", serde_json::json!({ "message": format!("'{ch_name}' UDP bind {bind_addr} failed: {e}") }));
            return;
        }
    };
    socket.set_read_timeout(Some(Duration::from_millis(50))).ok();
    let _ = app.emit("engine-log", serde_json::json!({ "message": format!("RECV '{ch_name}' ← {bind_addr}") }));
    let _ = app.emit("channel-status", serde_json::json!({ "id": ch_id, "status": "active" }));
    crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_status","id":ch_id,"status":"active"}).to_string());

    let mut buf        = vec![0u8; 65536];
    let mut meter      = LevelMeter::new(4800);
    let mut last_emit  = Instant::now();
    let mut last_audio = Instant::now();
    let mut first_recv = true;
    const  EMIT_MS:    Duration = Duration::from_millis(80);
    const  SILENCE_MS: Duration = Duration::from_millis(150);

    loop {
        if stop.load(Ordering::SeqCst) { break; }
        match socket.recv_from(&mut buf) {
            Ok((n, src)) if n >= 4 => {
                last_audio = Instant::now();
                if first_recv {
                    first_recv = false;
                    let _ = app.emit("engine-log", serde_json::json!({
                        "message": format!("RECV '{ch_name}' ← first packet from {src} ({n} bytes) on {bind_addr}")
                    }));
                }
                let volume = vol.load(Ordering::Relaxed) as f32 / 10_000.0;
                let samples: Vec<f32> = buf[..n].chunks_exact(4)
                    .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]) * volume)
                    .collect();
                meter.push(&samples);
                let _ = tx.try_send(samples);
                if last_emit.elapsed() >= EMIT_MS {
                    let level = meter.level();
                    let _ = app.emit("channel-level", serde_json::json!({ "id": ch_id, "level": level }));
                    let _ = app.emit("channel-status", serde_json::json!({ "id": ch_id, "status": "active" }));
                    crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_level","id":ch_id,"level":level}).to_string());
                    crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_status","id":ch_id,"status":"active"}).to_string());
                    last_emit = Instant::now();
                }
            }
            Ok(_) => {}
            Err(ref e) if e.kind() == std::io::ErrorKind::TimedOut
                       || e.kind() == std::io::ErrorKind::WouldBlock => {
                if last_audio.elapsed() > SILENCE_MS && last_emit.elapsed() >= EMIT_MS {
                    let _ = app.emit("channel-level", serde_json::json!({ "id": ch_id, "level": 0.0 }));
                    crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_level","id":ch_id,"level":0.0}).to_string());
                    last_emit = Instant::now();
                }
            }
            Err(e) => {
                let _ = app.emit("engine-error", serde_json::json!({ "message": format!("'{ch_name}' UDP recv error: {e}") }));
                break;
            }
        }
    }
    drop(tx);
    let _ = app.emit("channel-level",  serde_json::json!({ "id": ch_id, "level": 0.0 }));
    let _ = app.emit("channel-status", serde_json::json!({ "id": ch_id, "status": "idle" }));
    crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_level","id":ch_id,"level":0.0}).to_string());
    crate::websocket::broadcast(&ws, serde_json::json!({"event":"channel_status","id":ch_id,"status":"idle"}).to_string());
}
