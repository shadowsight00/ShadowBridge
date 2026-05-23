use crate::config::{ChannelConfig, Config};
use crate::state::AppState;
use tauri::State;

#[tauri::command]
pub fn get_loopback_devices() -> Vec<String> {
    use cpal::traits::{DeviceTrait, HostTrait};
    cpal::default_host()
        .output_devices()
        .map(|it| it.filter_map(|d| d.name().ok()).collect())
        .unwrap_or_default()
}

#[tauri::command]
pub fn get_output_devices() -> Vec<String> {
    use cpal::traits::{DeviceTrait, HostTrait};
    cpal::default_host()
        .output_devices()
        .map(|it| it.filter_map(|d| d.name().ok()).collect())
        .unwrap_or_default()
}

#[tauri::command]
pub fn get_input_devices() -> Vec<String> {
    #[cfg(windows)]
    {
        use wasapi::{initialize_mta, DeviceCollection, Direction};
        let _ = initialize_mta();
        let Ok(collection) = DeviceCollection::new(&Direction::Capture) else {
            return vec![];
        };
        let count = collection.get_nbr_devices().unwrap_or(0);
        let mut names = Vec::new();
        for i in 0..count {
            if let Ok(device) = collection.get_device_at_index(i) {
                if let Ok(name) = device.get_friendlyname() {
                    names.push(name);
                }
            }
        }
        names.sort_unstable();
        names
    }
    #[cfg(not(windows))]
    {
        use cpal::traits::{DeviceTrait, HostTrait};
        cpal::default_host()
            .input_devices()
            .map(|it| it.filter_map(|d| d.name().ok()).collect())
            .unwrap_or_default()
    }
}

#[tauri::command]
pub fn get_app_audio_sources() -> Vec<String> {
    #[cfg(windows)]
    return wasapi_session_names();
    #[cfg(not(windows))]
    return vec![];
}

/// Enumerate active WASAPI audio sessions and return their process names.
/// Runs on a dedicated thread to avoid COM apartment conflicts.
#[cfg(windows)]
fn wasapi_session_names() -> Vec<String> {
    std::thread::spawn(|| unsafe { enum_sessions().unwrap_or_default() })
        .join()
        .unwrap_or_default()
}

#[cfg(windows)]
unsafe fn enum_sessions() -> anyhow::Result<Vec<String>> {
    use windows::core::Interface as _;
    use windows::Win32::Foundation::BOOL;
    use windows::Win32::Media::Audio::{
        eRender, AudioSessionState, IAudioSessionControl2, IAudioSessionEnumerator,
        IAudioSessionManager2, IMMDeviceCollection, IMMDeviceEnumerator,
        MMDeviceEnumerator, DEVICE_STATE_ACTIVE,
    };
    use windows::Win32::System::Com::{
        CoCreateInstance, CoInitializeEx, CoUninitialize, CLSCTX_ALL, COINIT_MULTITHREADED,
    };
    use windows::Win32::System::Threading::{
        OpenProcess, QueryFullProcessImageNameW, PROCESS_NAME_WIN32,
        PROCESS_QUERY_LIMITED_INFORMATION,
    };

    let _ = CoInitializeEx(None, COINIT_MULTITHREADED);

    let result = (|| -> anyhow::Result<Vec<String>> {
        let enumerator: IMMDeviceEnumerator =
            CoCreateInstance(&MMDeviceEnumerator, None, CLSCTX_ALL)?;

        // Enumerate ALL active render endpoints so we catch apps that have
        // been assigned a non-default device via Windows per-app audio settings.
        let collection: IMMDeviceCollection =
            enumerator.EnumAudioEndpoints(eRender, DEVICE_STATE_ACTIVE)?;

        let device_count = collection.GetCount()?;
        let mut names: Vec<String> = Vec::new();

        for dev_idx in 0..device_count {
            let device = match collection.Item(dev_idx) {
                Ok(d)  => d,
                Err(_) => continue,
            };
            let mgr: IAudioSessionManager2 = match device.Activate(CLSCTX_ALL, None) {
                Ok(m)  => m,
                Err(_) => continue,
            };
            let sess_enum: IAudioSessionEnumerator = match mgr.GetSessionEnumerator() {
                Ok(e)  => e,
                Err(_) => continue,
            };
            let sess_count = match sess_enum.GetCount() {
                Ok(n)  => n,
                Err(_) => continue,
            };

            for sess_idx in 0..sess_count {
                let ctrl = match sess_enum.GetSession(sess_idx) {
                    Ok(c)  => c,
                    Err(_) => continue,
                };

                // AudioSessionStateExpired (2) means the process has ended — skip it.
                if let Ok(state) = ctrl.GetState() {
                    if state == AudioSessionState(2) { continue; }
                }

                let ctrl2: IAudioSessionControl2 = match ctrl.cast() {
                    Ok(c)  => c,
                    Err(_) => continue,
                };
                let pid = match ctrl2.GetProcessId() {
                    Ok(p)  => p,
                    Err(_) => continue,
                };
                if pid == 0 { continue; } // system-wide audio session

                let handle = match OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, BOOL(0), pid) {
                    Ok(h)  => h,
                    Err(_) => continue,
                };
                let mut buf = [0u16; 260];
                let mut len = buf.len() as u32;
                let ok = QueryFullProcessImageNameW(
                    handle,
                    PROCESS_NAME_WIN32,
                    windows::core::PWSTR(buf.as_mut_ptr()),
                    &mut len,
                );
                let _ = windows::Win32::Foundation::CloseHandle(handle);
                if ok.is_err() { continue; }

                let path = String::from_utf16_lossy(&buf[..len as usize]);
                let stem = std::path::Path::new(&path)
                    .file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("")
                    .to_string();
                if !stem.is_empty() && !names.contains(&stem) {
                    names.push(stem);
                }
            }
        }

        names.sort_unstable();
        Ok(names)
    })();

    CoUninitialize();
    result
}

#[tauri::command]
pub fn get_local_ip() -> String {
    use std::net::UdpSocket;
    UdpSocket::bind("0.0.0.0:0")
        .and_then(|s| { s.connect("8.8.8.8:80")?; s.local_addr() })
        .map(|a| a.ip().to_string())
        .unwrap_or_else(|_| "127.0.0.1".to_string())
}

#[tauri::command]
pub fn start_monitoring(
    app:      tauri::AppHandle,
    state:    State<'_, AppState>,
    channels: Vec<ChannelConfig>,
) {
    state.monitor.lock().start(channels, app);
}

#[tauri::command]
pub fn stop_monitoring(state: State<'_, AppState>) {
    state.monitor.lock().stop();
}

#[tauri::command]
pub fn restart_monitor_channel(
    app:     tauri::AppHandle,
    state:   State<'_, AppState>,
    channel: ChannelConfig,
) {
    state.monitor.lock().restart_channel(channel, app);
}

#[tauri::command]
pub fn load_config(state: State<AppState>) -> Config {
    state.config.lock().clone()
}

#[tauri::command]
pub fn save_config(state: State<AppState>, config: Config) -> Result<(), String> {
    config.save().map_err(|e| e.to_string())?;
    *state.config.lock() = config;
    Ok(())
}

#[tauri::command]
pub fn start_engine(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
    channels: Vec<ChannelConfig>,
    dest_ip: String,
    mode: String,
) -> Result<(), String> {
    use std::sync::atomic::Ordering;
    use tauri::Emitter;
    let (sample_rate, buffer_size, buffer_offset_ms) = {
        let cfg = state.config.lock();
        (cfg.sample_rate, cfg.buffer_size, cfg.buffer_offset_ms)
    };
    match state.engine.lock().start(
        channels, &dest_ip, &mode, app.clone(),
        sample_rate, buffer_size, buffer_offset_ms,
    ) {
        Ok(()) => {
            state.engine_running.store(true, Ordering::Relaxed);
            crate::tray::update_stream_item(&app, true);
            crate::websocket::broadcast(&state.ws_clients,
                serde_json::json!({"event":"streaming_started"}).to_string());
            Ok(())
        }
        Err(e) => {
            let msg = e.to_string();
            let _ = app.emit("engine-error", serde_json::json!({ "message": msg }));
            Err(msg)
        }
    }
}

#[tauri::command]
pub fn stop_engine(app: tauri::AppHandle, state: State<'_, AppState>) -> Result<(), String> {
    use std::sync::atomic::Ordering;
    state.engine.lock().stop();
    state.engine_running.store(false, Ordering::Relaxed);
    crate::tray::update_stream_item(&app, false);
    crate::websocket::broadcast(&state.ws_clients,
        serde_json::json!({"event":"streaming_stopped"}).to_string());
    Ok(())
}

#[tauri::command]
pub async fn send_peer_command(peer_ip: String, cmd: String) -> Result<(), String> {
    crate::net::control::send_control_command(&peer_ip, &cmd)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn restart_engine_channel(
    app:     tauri::AppHandle,
    state:   State<'_, AppState>,
    channel: crate::config::ChannelConfig,
) -> Result<(), String> {
    use std::sync::atomic::Ordering;
    if state.engine_running.load(Ordering::Relaxed) {
        state.engine.lock().restart_channel(channel, app);
    }
    Ok(())
}

#[tauri::command]
pub fn set_channel_volume(state: State<'_, AppState>, channel_id: String, volume: f32) {
    state.engine.lock().set_volume(&channel_id, volume / 100.0);
    {
        let mut cfg = state.config.lock();
        let channels = if cfg.mode == "gaming" {
            &mut cfg.gaming_channels
        } else {
            &mut cfg.streaming_channels
        };
        if let Some(ch) = channels.iter_mut().find(|c| c.id == channel_id) {
            ch.volume = volume as u32;
        }
    }
    let vol_u32 = volume as u32;
    crate::websocket::broadcast(
        &state.ws_clients,
        serde_json::json!({"event": "channel_volume", "id": channel_id, "volume": vol_u32}).to_string(),
    );
}

#[tauri::command]
pub async fn get_autostart(app: tauri::AppHandle) -> bool {
    use tauri_plugin_autostart::ManagerExt;
    app.autolaunch().is_enabled().unwrap_or(false)
}

#[tauri::command]
pub async fn set_autostart(app: tauri::AppHandle, enabled: bool) -> Result<(), String> {
    use tauri_plugin_autostart::ManagerExt;
    if enabled {
        app.autolaunch().enable().map_err(|e| e.to_string())
    } else {
        app.autolaunch().disable().map_err(|e| e.to_string())
    }
}

#[tauri::command]
pub fn broadcast_channel_appearance(
    state:              State<'_, AppState>,
    channel_id:         String,
    name:               String,
    color:              String,
    icon:               String,
    custom_icon_base64: Option<String>,
) {
    let icon_id = if icon.starts_with("data:") || icon.starts_with("http") {
        serde_json::Value::Null
    } else {
        serde_json::Value::String(
            icon.trim_start_matches("ti-").trim_start_matches("brand:").to_string()
        )
    };
    crate::websocket::broadcast(
        &state.ws_clients,
        serde_json::json!({
            "event":            "channel_appearance",
            "id":               channel_id,
            "name":             name,
            "color":            color,
            "icon":             icon,
            "iconId":           icon_id,
            "customIconBase64": custom_icon_base64,
        }).to_string(),
    );
}
