use anyhow::Result;
use std::net::SocketAddr;
use tokio::net::UdpSocket;

/// Packet layout: [channel_tag: u8][f32 LE samples...]
const HEADER_LEN: usize = 1;
const MAX_SAMPLES_PER_PACKET: usize = (65507 - HEADER_LEN) / 4; // stay under UDP MTU

pub struct UdpSender {
    socket: UdpSocket,
    dest: SocketAddr,
}

impl UdpSender {
    pub async fn connect(bind: &str, dest: SocketAddr) -> Result<Self> {
        let socket = UdpSocket::bind(bind).await?;
        Ok(Self { socket, dest })
    }

    pub async fn send_chunk(&self, tag: u8, samples: &[f32]) -> Result<()> {
        for chunk in samples.chunks(MAX_SAMPLES_PER_PACKET) {
            let mut buf = Vec::with_capacity(HEADER_LEN + chunk.len() * 4);
            buf.push(tag);
            for &s in chunk {
                buf.extend_from_slice(&s.to_le_bytes());
            }
            self.socket.send_to(&buf, self.dest).await?;
        }
        Ok(())
    }
}

pub struct UdpReceiver {
    socket: UdpSocket,
}

impl UdpReceiver {
    pub async fn bind(addr: &str) -> Result<Self> {
        let socket = UdpSocket::bind(addr).await?;
        Ok(Self { socket })
    }

    /// Returns `(tag, samples, peer_addr)`.
    pub async fn recv_chunk(&self) -> Result<(u8, Vec<f32>, SocketAddr)> {
        let mut buf = vec![0u8; 65536];
        let (n, addr) = self.socket.recv_from(&mut buf).await?;
        anyhow::ensure!(n > HEADER_LEN, "packet too short");
        let tag = buf[0];
        let samples = buf[HEADER_LEN..n]
            .chunks_exact(4)
            .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
            .collect();
        Ok((tag, samples, addr))
    }
}
