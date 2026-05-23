mod audio;
mod commands;
mod config;
mod net;
mod state;
mod tray;
mod websocket;

use std::{
    collections::HashMap,
    sync::Arc,
    time::{Duration, Instant},
};

use config::Config;
use parking_lot::Mutex;
use state::AppState;
use tauri::Emitter;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::init();

    migrate_legacy_config();

    let config = Config::load().unwrap_or_default();
    let app_state = AppState::new(config);

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            use tauri::Manager;
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.show();
                let _ = win.set_focus();
            }
        }))
        .manage(app_state)
        .setup(|app| {
            use tauri::Manager;
            tray::setup(app.handle())?;

            let cfg = app.state::<AppState>().config.lock().clone();

            let win = app.get_webview_window("main").expect("main window");
            if cfg.start_minimized {
                let _ = win.hide();
            }

            // Optionally hide instead of quit when the window's close button is clicked.
            let win_ref = win.clone();
            let config_for_close = app.state::<AppState>().config.clone();
            win.on_window_event(move |event| {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    if config_for_close.lock().tray_on_close {
                        api.prevent_close();
                        let _ = win_ref.hide();
                    }
                }
            });

            let disc_port  = cfg.discovery_port;
            let config_arc = app.state::<AppState>().config.clone();
            spawn_discovery(app.handle().clone(), config_arc, disc_port);
            net::control::spawn_control_listener(app.handle().clone());
            websocket::spawn_ws_server(app.handle().clone());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_loopback_devices,
            commands::get_output_devices,
            commands::get_input_devices,
            commands::get_app_audio_sources,
            commands::get_local_ip,
            commands::start_monitoring,
            commands::stop_monitoring,
            commands::restart_monitor_channel,
            commands::load_config,
            commands::save_config,
            commands::start_engine,
            commands::stop_engine,
            commands::set_channel_volume,
            commands::get_autostart,
            commands::set_autostart,
            commands::restart_engine_channel,
            commands::send_peer_command,
            commands::broadcast_channel_appearance,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

/// Migrate config from old AudioBridge / Python ShadowBridge locations.
fn migrate_legacy_config() {
    use directories::UserDirs;
    let Some(user_dirs) = UserDirs::new() else { return };
    let docs = user_dirs.document_dir().unwrap_or(user_dirs.home_dir());
    let dest = docs.join("ShadowBridge").join("config.json");
    if dest.exists() { return; }

    let legacy_paths = [
        docs.join("AudioBridge").join("config.json"),
        docs.join("ShadowBridge_old").join("config.json"),
    ];
    for src in &legacy_paths {
        if src.exists() {
            if let Some(parent) = dest.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            if std::fs::copy(src, &dest).is_ok() {
                log::info!("Migrated config from {} to {}", src.display(), dest.display());
            }
            return;
        }
    }
}

fn spawn_discovery(app: tauri::AppHandle, config: Arc<Mutex<Config>>, disc_port: u16) {
    use net::discovery::{DiscoveryBeacon, MAGIC};
    use tokio::net::UdpSocket;

    // Broadcaster: announce presence every 5 s.
    let config_b = Arc::clone(&config);
    tauri::async_runtime::spawn(async move {
        let disc = net::discovery::Discovery::new(disc_port);
        loop {
            let mode = { config_b.lock().mode.clone() };
            if let Err(e) = disc.broadcast_once(&mode).await {
                log::warn!("discovery broadcast: {e}");
            }
            tokio::time::sleep(Duration::from_secs(5)).await;
        }
    });

    // Listener: emit peer-found / peer-lost.
    let own_hostname = gethostname::gethostname()
        .into_string()
        .unwrap_or_default();

    tauri::async_runtime::spawn(async move {
        let socket = match UdpSocket::bind(format!("0.0.0.0:{disc_port}")).await {
            Ok(s)  => s,
            Err(e) => { log::error!("discovery listener bind: {e}"); return; }
        };

        let mut last_seen: HashMap<String, Instant> = HashMap::new();
        let mut last_janitor = Instant::now();
        let mut buf = [0u8; 1024];

        loop {
            match tokio::time::timeout(Duration::from_secs(5), socket.recv_from(&mut buf)).await {
                Ok(Ok((n, addr))) => {
                    if n > MAGIC.len() && &buf[..MAGIC.len()] == MAGIC {
                        if let Ok(beacon) = serde_json::from_slice::<DiscoveryBeacon>(&buf[MAGIC.len()..n]) {
                            if beacon.hostname != own_hostname {
                                let ip = addr.ip().to_string();
                                let is_new = !last_seen.contains_key(&ip);
                                last_seen.insert(ip.clone(), Instant::now());
                                if is_new {
                                    let _ = app.emit("peer-found",
                                        serde_json::json!({ "ip": ip, "mode": beacon.mode }));
                                    use tauri::Manager;
                                    let st = app.state::<AppState>();
                                    *st.peer_ip.lock() = Some(ip.clone());
                                    websocket::broadcast(&st.ws_clients,
                                        serde_json::json!({"event":"peer_connected","ip":ip}).to_string());
                                }
                            }
                        }
                    }
                }
                Ok(Err(e)) => { log::error!("discovery recv: {e}"); break; }
                Err(_) => {}
            }

            if last_janitor.elapsed() >= Duration::from_secs(5) {
                let now = Instant::now();
                let expired: Vec<String> = last_seen.iter()
                    .filter(|(_, t)| now.duration_since(**t) > Duration::from_secs(15))
                    .map(|(k, _)| k.clone())
                    .collect();
                for ip in expired {
                    last_seen.remove(&ip);
                    let _ = app.emit("peer-lost", serde_json::json!({ "ip": ip }));
                    use tauri::Manager;
                    let st = app.state::<AppState>();
                    *st.peer_ip.lock() = None;
                    websocket::broadcast(&st.ws_clients,
                        serde_json::json!({"event":"peer_lost"}).to_string());
                }
                last_janitor = Instant::now();
            }
        }
    });
}
