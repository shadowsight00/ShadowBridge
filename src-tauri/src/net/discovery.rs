use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use tokio::net::UdpSocket;

pub const MAGIC: &[u8] = b"SBRDG\x00";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoveryBeacon {
    pub hostname: String,
    pub version:  String,
    pub mode:     String,
}

pub struct Discovery {
    port: u16,
}

impl Discovery {
    pub fn new(port: u16) -> Self {
        Self { port }
    }

    /// Broadcast our presence once. `mode` is "gaming" or "streaming".
    pub async fn broadcast_once(&self, mode: &str) -> Result<()> {
        let socket = UdpSocket::bind("0.0.0.0:0").await?;
        socket.set_broadcast(true)?;

        let beacon = DiscoveryBeacon {
            hostname: gethostname::gethostname()
                .into_string()
                .unwrap_or_else(|_| "unknown".to_string()),
            version: env!("CARGO_PKG_VERSION").to_string(),
            mode:    mode.to_string(),
        };

        let mut payload = MAGIC.to_vec();
        payload.extend_from_slice(&serde_json::to_vec(&beacon)?);

        let dest: SocketAddr = format!("255.255.255.255:{}", self.port).parse()?;
        socket.send_to(&payload, dest).await?;
        Ok(())
    }

    /// Blocks until a valid beacon arrives; returns sender address + beacon.
    pub async fn listen_once(&self) -> Result<(SocketAddr, DiscoveryBeacon)> {
        let socket = UdpSocket::bind(format!("0.0.0.0:{}", self.port)).await?;
        let mut buf = [0u8; 1024];
        loop {
            let (n, addr) = socket.recv_from(&mut buf).await?;
            if n <= MAGIC.len() || &buf[..MAGIC.len()] != MAGIC {
                continue;
            }
            if let Ok(beacon) =
                serde_json::from_slice::<DiscoveryBeacon>(&buf[MAGIC.len()..n])
            {
                return Ok((addr, beacon));
            }
        }
    }
}
