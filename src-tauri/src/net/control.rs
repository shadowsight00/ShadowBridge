use std::time::Duration;
use tauri::{AppHandle, Emitter};
use tokio::net::UdpSocket;

pub const CONTROL_PORT: u16 = 5099;

/// Spawn a permanent async task that listens for peer control commands on CONTROL_PORT.
/// Emits "peer-command" to the frontend when a valid {"cmd":"start_all"|"stop_all"} is received.
pub fn spawn_control_listener(app: AppHandle) {
    tauri::async_runtime::spawn(async move {
        let socket = match UdpSocket::bind(format!("0.0.0.0:{CONTROL_PORT}")).await {
            Ok(s)  => s,
            Err(e) => { log::error!("control listener bind :{CONTROL_PORT}: {e}"); return; }
        };
        log::info!("Control listener running on :{CONTROL_PORT}");

        let mut buf = [0u8; 256];
        loop {
            match tokio::time::timeout(Duration::from_secs(5), socket.recv_from(&mut buf)).await {
                Ok(Ok((n, _addr))) => {
                    if let Ok(text) = std::str::from_utf8(&buf[..n]) {
                        if let Ok(val) = serde_json::from_str::<serde_json::Value>(text) {
                            if let Some(cmd) = val.get("cmd").and_then(|v| v.as_str()) {
                                if matches!(cmd, "start_all" | "stop_all") {
                                    log::info!("Control: received '{cmd}' from peer");
                                    let _ = app.emit("peer-command",
                                        serde_json::json!({ "cmd": cmd }));
                                }
                            }
                        }
                    }
                }
                Ok(Err(e)) => { log::error!("control recv: {e}"); break; }
                Err(_)     => {} // 5 s timeout — keep looping
            }
        }
    });
}

/// Fire-and-forget: send a control command to `peer_ip` on CONTROL_PORT.
pub async fn send_control_command(peer_ip: &str, cmd: &str) -> anyhow::Result<()> {
    let socket = UdpSocket::bind("0.0.0.0:0").await?;
    let msg    = serde_json::json!({ "cmd": cmd }).to_string();
    socket.send_to(msg.as_bytes(), format!("{peer_ip}:{CONTROL_PORT}")).await?;
    Ok(())
}
