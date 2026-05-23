pub mod control;
pub mod discovery;
pub mod udp;
pub mod websocket;

use std::net::SocketAddr;
use self::discovery::Discovery;
use self::websocket::WsServer;

pub struct NetworkManager {
    ws_port: u16,
    discovery_port: u16,
    peer_addr: Option<SocketAddr>,
}

impl NetworkManager {
    pub fn new(ws_port: u16, discovery_port: u16) -> Self {
        Self { ws_port, discovery_port, peer_addr: None }
    }

    pub fn peer_addr(&self) -> Option<SocketAddr> { self.peer_addr }
    pub fn set_peer_addr(&mut self, addr: SocketAddr) { self.peer_addr = Some(addr); }

    /// Spawn the WebSocket control server (non-blocking).
    pub fn spawn_ws_server(&self) -> tokio::task::JoinHandle<()> {
        let server = WsServer::new(self.ws_port);
        tokio::spawn(async move {
            if let Err(e) = server.run().await {
                log::error!("WS server: {e}");
            }
        })
    }

    /// Spawn a periodic discovery broadcast every 5 s (non-blocking).
    pub fn spawn_discovery_broadcast(&self) -> tokio::task::JoinHandle<()> {
        let port = self.discovery_port;
        tokio::spawn(async move {
            let disc = Discovery::new(port);
            loop {
                if let Err(e) = disc.broadcast_once("gaming").await {
                    log::warn!("discovery broadcast: {e}");
                }
                tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
            }
        })
    }

    /// Await a single discovery beacon from a peer.
    pub async fn await_peer_discovery(&self) -> anyhow::Result<SocketAddr> {
        let disc = Discovery::new(self.discovery_port);
        let (addr, beacon) = disc.listen_once().await?;
        log::info!("discovered peer {} ({})", addr, beacon.hostname);
        Ok(addr)
    }
}
