use anyhow::Result;
use std::sync::atomic::Ordering;
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager,
};

use crate::state::AppState;

const TRAY_ID: &str = "shadowbridge";

pub fn setup(app: &AppHandle) -> Result<()> {
    let menu = build_menu(app, false)?;

    TrayIconBuilder::with_id(TRAY_ID)
        .icon(app.default_window_icon().cloned().unwrap())
        .tooltip("ShadowBridge")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show"   => bring_to_front(app),
            "stream" => toggle_streaming(app),
            "quit"   => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                bring_to_front(tray.app_handle());
            }
        })
        .build(app)?;

    Ok(())
}

/// Rebuild and replace the tray menu, reflecting current streaming state.
pub fn update_stream_item(app: &AppHandle, running: bool) {
    let Some(tray) = app.tray_by_id(TRAY_ID) else { return };
    if let Ok(menu) = build_menu(app, running) {
        let _ = tray.set_menu(Some(menu));
    }
}

fn build_menu(app: &AppHandle, running: bool) -> Result<Menu<tauri::Wry>> {
    let stream_label = if running { "■  Stop Streaming" } else { "▶  Start Streaming" };
    let show   = MenuItem::with_id(app, "show",   "Show Window",  true, None::<&str>)?;
    let sep1   = PredefinedMenuItem::separator(app)?;
    let stream = MenuItem::with_id(app, "stream", stream_label,  true, None::<&str>)?;
    let sep2   = PredefinedMenuItem::separator(app)?;
    let quit   = MenuItem::with_id(app, "quit",   "Quit",         true, None::<&str>)?;
    Ok(Menu::with_items(app, &[&show, &sep1, &stream, &sep2, &quit])?)
}

fn bring_to_front(app: &AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.show();
        let _ = win.set_focus();
    }
}

fn toggle_streaming(app: &AppHandle) {
    let state = app.state::<AppState>();
    if state.engine_running.load(Ordering::Relaxed) {
        state.engine.lock().stop();
        state.engine_running.store(false, Ordering::Relaxed);
        update_stream_item(app, false);
        let _ = app.emit("engine-stopped-tray", ());
    } else {
        let cfg = state.config.lock().clone();
        let channels = if cfg.mode == "gaming" {
            cfg.gaming_channels.clone()
        } else {
            cfg.streaming_channels.clone()
        };
        let dest_ip = if cfg.mode == "gaming" {
            cfg.streaming_ip.clone()
        } else {
            cfg.gaming_ip.clone()
        };
        match state.engine.lock().start(
            channels, &dest_ip, &cfg.mode, app.clone(),
            cfg.sample_rate, cfg.buffer_size, cfg.buffer_offset_ms,
        ) {
            Ok(()) => {
                state.engine_running.store(true, Ordering::Relaxed);
                update_stream_item(app, true);
                let _ = app.emit("engine-started-tray", ());
            }
            Err(e) => {
                let _ = app.emit("engine-error", serde_json::json!({ "message": e.to_string() }));
            }
        }
    }
}
