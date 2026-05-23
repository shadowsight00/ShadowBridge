use anyhow::Result;
use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use tokio::net::{TcpListener, TcpStream};
use tokio_tungstenite::{accept_async, tungstenite::Message};

/// Commands accepted from external WebSocket clients.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WsCommand {
    SetVolume { channel_id: String, volume: f32 },
    StartChannel { channel_id: String },
    StopChannel { channel_id: String },
    StartAll,
    StopAll,
    GetStatus,
}

/// Events pushed to WebSocket clients.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WsEvent {
    pub event: String,
    pub data: serde_json::Value,
}

pub struct WsServer {
    port: u16,
}

impl WsServer {
    pub fn new(port: u16) -> Self {
        Self { port }
    }

    pub async fn run(self) -> Result<()> {
        let listener = TcpListener::bind(format!("0.0.0.0:{}", self.port)).await?;
        log::info!("WebSocket server on :{}", self.port);
        while let Ok((stream, addr)) = listener.accept().await {
            tokio::spawn(Self::handle(stream, addr));
        }
        Ok(())
    }

    async fn handle(stream: TcpStream, addr: SocketAddr) {
        log::debug!("WS connect from {addr}");
        let Ok(mut ws) = accept_async(stream).await else { return };
        while let Some(Ok(msg)) = ws.next().await {
            match msg {
                Message::Text(text) => {
                    match serde_json::from_str::<WsCommand>(&text) {
                        Ok(cmd) => {
                            log::debug!("WS cmd {cmd:?}");
                            // TODO: forward cmd to AppState via an mpsc sender
                        }
                        Err(e) => log::warn!("bad WS msg from {addr}: {e}"),
                    }
                }
                Message::Close(_) => break,
                _ => {}
            }
        }
        log::debug!("WS disconnect {addr}");
    }
}
