use parking_lot::Mutex;
use std::sync::Arc;
use std::sync::atomic::AtomicBool;
use crate::config::Config;
use crate::audio::{AudioEngine, MonitoringEngine};
use crate::websocket::WsClients;

pub struct AppState {
    pub config:          Arc<Mutex<Config>>,
    pub engine:          Arc<Mutex<AudioEngine>>,
    pub engine_running:  Arc<AtomicBool>,
    pub monitor:         Arc<Mutex<MonitoringEngine>>,
    pub ws_clients:      WsClients,
    /// IP of currently connected peer, if any.
    pub peer_ip:         Arc<Mutex<Option<String>>>,
}

impl AppState {
    pub fn new(config: Config) -> Self {
        Self {
            config:         Arc::new(Mutex::new(config)),
            engine:         Arc::new(Mutex::new(AudioEngine::new())),
            engine_running: Arc::new(AtomicBool::new(false)),
            monitor:        Arc::new(Mutex::new(MonitoringEngine::new())),
            ws_clients:     crate::websocket::new_clients(),
            peer_ip:        Arc::new(Mutex::new(None)),
        }
    }
}
