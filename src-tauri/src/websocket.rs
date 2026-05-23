use std::{collections::HashMap, sync::Arc};

use futures_util::{SinkExt, StreamExt};
use parking_lot::Mutex;
use serde_json::json;
use tauri::{Emitter, Manager};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::mpsc::{self, UnboundedSender};
use tokio_tungstenite::{accept_async, tungstenite::Message};

use crate::state::AppState;

/// Shared list of per-client outgoing senders.
pub type WsClients = Arc<Mutex<Vec<UnboundedSender<Message>>>>;

pub fn new_clients() -> WsClients {
    Arc::new(Mutex::new(Vec::new()))
}

/// Broadcast a JSON string to every connected client; drop dead ones.
pub fn broadcast(clients: &WsClients, msg: String) {
    clients
        .lock()
        .retain(|tx| tx.send(Message::Text(msg.clone())).is_ok());
}

/// Spawn the WebSocket server as a background Tokio task.
pub fn spawn_ws_server(app: tauri::AppHandle) {
    tauri::async_runtime::spawn(async move {
        if let Err(e) = run_server(app).await {
            log::error!("WS server fatal: {e}");
        }
    });
}

async fn run_server(app: tauri::AppHandle) -> anyhow::Result<()> {
    let listener = TcpListener::bind("127.0.0.1:8765").await?;
    log::info!("WebSocket server listening on ws://127.0.0.1:8765");

    // Pre-mute volume map: channel_id → AtomicU32 units (0..10_000)
    let pre_mute: Arc<Mutex<HashMap<String, u32>>> = Arc::new(Mutex::new(HashMap::new()));

    loop {
        let (stream, addr) = listener.accept().await?;
        log::debug!("WS client connected: {addr}");
        let app2 = app.clone();
        let pm2 = Arc::clone(&pre_mute);
        tokio::spawn(async move {
            if let Err(e) = handle_connection(stream, app2, pm2).await {
                log::debug!("WS client {addr} closed: {e}");
            }
        });
    }
}

async fn handle_connection(
    stream: TcpStream,
    app: tauri::AppHandle,
    pre_mute: Arc<Mutex<HashMap<String, u32>>>,
) -> anyhow::Result<()> {
    let ws = accept_async(stream).await?;
    let (ws_tx, mut ws_rx) = ws.split();

    // Per-client outgoing channel — messages sent here flow to the WebSocket.
    let (tx, mut rx) = mpsc::unbounded_channel::<Message>();

    // Register this client.
    {
        let state = app.state::<AppState>();
        state.ws_clients.lock().push(tx.clone());
    }

    // Forward channel → WebSocket on its own task.
    let mut ws_tx = ws_tx;
    tokio::spawn(async move {
        while let Some(msg) = rx.recv().await {
            if ws_tx.send(msg).await.is_err() {
                break;
            }
        }
    });

    // Read incoming messages and dispatch commands.
    while let Some(result) = ws_rx.next().await {
        match result {
            Ok(Message::Text(text)) => {
                handle_command(&text, &app, &pre_mute, &tx).await;
            }
            Ok(Message::Ping(p)) => {
                let _ = tx.send(Message::Pong(p));
            }
            Ok(Message::Close(_)) | Err(_) => break,
            _ => {}
        }
    }

    // Client gone — next broadcast will prune the dead sender via retain.
    Ok(())
}

async fn handle_command(
    text: &str,
    app: &tauri::AppHandle,
    pre_mute: &Arc<Mutex<HashMap<String, u32>>>,
    reply: &UnboundedSender<Message>,
) {
    let val: serde_json::Value = match serde_json::from_str(text) {
        Ok(v) => v,
        Err(_) => {
            log::warn!("WS: invalid JSON: {text}");
            return;
        }
    };

    let cmd = match val.get("cmd").and_then(|v| v.as_str()) {
        Some(c) => c.to_string(),
        None => {
            log::warn!("WS: no 'cmd' field in: {text}");
            return;
        }
    };

    let state = app.state::<AppState>();

    match cmd.as_str() {
        // ── Start streaming ───────────────────────────────────────────────────
        "start_all" => {
            use std::sync::atomic::Ordering;
            if state.engine.lock().is_running() {
                return;
            }
            let (channels, dest_ip, mode, sr, bs, boms) = {
                let cfg = state.config.lock();
                let is_gaming = cfg.mode == "gaming";
                let ch = if is_gaming {
                    cfg.gaming_channels.clone()
                } else {
                    cfg.streaming_channels.clone()
                };
                let ip = if is_gaming {
                    cfg.streaming_ip.clone()
                } else {
                    cfg.gaming_ip.clone()
                };
                (ch, ip, cfg.mode.clone(), cfg.sample_rate, cfg.buffer_size, cfg.buffer_offset_ms)
            };
            let result = state.engine.lock().start(
                channels, &dest_ip, &mode, app.clone(), sr, bs, boms,
            );
            if result.is_ok() {
                use tauri::Emitter;
                state.engine_running.store(true, Ordering::Relaxed);
                crate::tray::update_stream_item(app, true);
                broadcast(&state.ws_clients, json!({"event": "streaming_started"}).to_string());
                let _ = app.emit("engine-started-tray", ());
                // Also tell the peer to start
                if let Some(peer_ip) = state.peer_ip.lock().clone() {
                    tauri::async_runtime::spawn(async move {
                        let _ = crate::net::control::send_control_command(&peer_ip, "start_all").await;
                    });
                }
            }
        }

        // ── Stop streaming ────────────────────────────────────────────────────
        "stop_all" => {
            use std::sync::atomic::Ordering;
            use tauri::Emitter;
            state.engine.lock().stop();
            state.engine_running.store(false, Ordering::Relaxed);
            crate::tray::update_stream_item(app, false);
            broadcast(&state.ws_clients, json!({"event": "streaming_stopped"}).to_string());
            let _ = app.emit("engine-stopped-tray", ());
            // Also tell the peer to stop
            if let Some(peer_ip) = state.peer_ip.lock().clone() {
                tauri::async_runtime::spawn(async move {
                    let _ = crate::net::control::send_control_command(&peer_ip, "stop_all").await;
                });
            }
        }

        // ── Toggle channel enabled ────────────────────────────────────────────
        "toggle_channel" => {
            use std::sync::atomic::Ordering;
            let id = match val.get("id").and_then(|v| v.as_str()) {
                Some(s) => s.to_string(),
                None => return,
            };
            let (new_enabled, channel_clone) = {
                let mut cfg = state.config.lock();
                let is_gaming = cfg.mode == "gaming";
                let channels = if is_gaming {
                    &mut cfg.gaming_channels
                } else {
                    &mut cfg.streaming_channels
                };
                if let Some(ch) = channels.iter_mut().find(|c| c.id == id) {
                    ch.enabled = !ch.enabled;
                    (ch.enabled, Some(ch.clone()))
                } else {
                    (false, None)
                }
            };
            if let Some(ch) = channel_clone {
                let _ = state.config.lock().save();
                broadcast(
                    &state.ws_clients,
                    json!({
                        "event":            "channel_toggled",
                        "id":               id,
                        "enabled":          new_enabled,
                        "name":             ch.name,
                        "color":            ch.color,
                        "icon":             ch.icon,
                        "customIconBase64": ch.custom_icon_base64,
                    }).to_string(),
                );
                let _ = app.emit("channel-toggled", json!({ "id": id, "enabled": new_enabled }));
                if state.engine_running.load(Ordering::Relaxed) {
                    state.engine.lock().restart_channel(ch, app.clone());
                }
            }
        }

        // ── Mute (set vol = 0, remember previous) ────────────────────────────
        "mute_channel" => {
            let id = match val.get("id").and_then(|v| v.as_str()) {
                Some(s) => s.to_string(),
                None => return,
            };
            let saved_vol = {
                let cfg = state.config.lock();
                let is_gaming = cfg.mode == "gaming";
                let channels = if is_gaming {
                    &cfg.gaming_channels
                } else {
                    &cfg.streaming_channels
                };
                channels
                    .iter()
                    .find(|c| c.id == id)
                    .map(|c| (c.volume as f32 / 100.0 * 10_000.0) as u32)
                    .unwrap_or(10_000)
            };
            pre_mute.lock().insert(id.clone(), saved_vol);
            state.engine.lock().set_volume(&id, 0.0);
        }

        // ── Unmute (restore remembered volume) ───────────────────────────────
        "unmute_channel" => {
            let id = match val.get("id").and_then(|v| v.as_str()) {
                Some(s) => s.to_string(),
                None => return,
            };
            let saved = pre_mute.lock().remove(&id).unwrap_or(10_000);
            state.engine.lock().set_volume(&id, saved as f32 / 10_000.0);
        }

        // ── Set volume (0-100) and persist ────────────────────────────────────
        "set_volume" => {
            let id = match val.get("id").and_then(|v| v.as_str()) {
                Some(s) => s.to_string(),
                None => return,
            };
            let value = match val.get("value").and_then(|v| v.as_f64()) {
                Some(v) => v.clamp(0.0, 100.0) as f32,
                None => return,
            };
            state.engine.lock().set_volume(&id, value / 100.0);
            {
                let mut cfg = state.config.lock();
                let is_gaming = cfg.mode == "gaming";
                let channels = if is_gaming {
                    &mut cfg.gaming_channels
                } else {
                    &mut cfg.streaming_channels
                };
                if let Some(ch) = channels.iter_mut().find(|c| c.id == id) {
                    ch.volume = value as u32;
                }
            }
            let _ = state.config.lock().save();
            let vol_u32 = value as u32;
            broadcast(
                &state.ws_clients,
                json!({"event": "channel_volume", "id": id, "volume": vol_u32}).to_string(),
            );
            use tauri::Emitter;
            let _ = app.emit("channel-volume", serde_json::json!({"id": id, "volume": vol_u32}));
        }

        // ── Full state snapshot (reply to requester only) ─────────────────────
        "get_state" => {
            let response = build_state_json(app);
            let _ = reply.send(Message::Text(response));
        }

        other => {
            log::warn!("WS: unknown command '{other}'");
        }
    }
}

/// Build the full-state JSON string for a get_state reply.
fn build_state_json(app: &tauri::AppHandle) -> String {
    use std::sync::atomic::Ordering;
    let state = app.state::<AppState>();
    let cfg = state.config.lock();
    let streaming = state.engine_running.load(Ordering::Relaxed);
    let peer_ip = state.peer_ip.lock().clone();
    let peer_connected = peer_ip.is_some();

    let channels: Vec<_> = {
        let all = if cfg.mode == "gaming" {
            &cfg.gaming_channels
        } else {
            &cfg.streaming_channels
        };
        all.iter()
            .map(|ch| {
                let status = if streaming && ch.enabled {
                    "active"
                } else {
                    "idle"
                };
                {
                    let icon_id = if ch.icon.starts_with("data:") || ch.icon.starts_with("http") {
                        serde_json::Value::Null
                    } else {
                        let s = ch.icon.trim_start_matches("ti-").trim_start_matches("brand:").to_string();
                        serde_json::Value::String(s)
                    };
                    json!({
                        "id":               ch.id,
                        "name":             ch.name,
                        "color":            ch.color,
                        "icon":             ch.icon,
                        "iconId":           icon_id,
                        "customIconBase64": ch.custom_icon_base64,
                        "direction":        ch.direction,
                        "enabled":          ch.enabled,
                        "volume":           ch.volume,
                        "status":           status,
                        "level":            0.0_f64,
                    })
                }
            })
            .collect()
    };

    json!({
        "event":         "state",
        "streaming":     streaming,
        "peer_connected": peer_connected,
        "peer_ip":       peer_ip,
        "mode":          cfg.mode,
        "channels":      channels,
    })
    .to_string()
}
