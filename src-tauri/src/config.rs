use serde::{Deserialize, Serialize};
use directories::UserDirs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChannelConfig {
    pub id: String,
    pub name: String,
    pub direction: String, // "OUT" | "IN" | "APP" | "MIC" | "MICOUT"
    pub device: String,
    pub port: u16,
    pub volume: u32, // 0–100
    pub color: String,
    pub icon: String,
    pub enabled: bool,
    #[serde(default)]
    pub custom_icon_base64: Option<String>,
}

fn default_buffer_size()       -> u32  { 1024  }
fn default_sample_rate()       -> u32  { 48_000 }
fn default_buffer_offset_ms()  -> u32  { 20    }
fn default_discovery_port()    -> u16  { 5999  }
fn default_command_port()      -> u16  { 8765  }
fn default_true()              -> bool { true  }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub mode: String,
    pub gaming_ip: String,
    pub streaming_ip: String,
    pub gaming_channels: Vec<ChannelConfig>,
    pub streaming_channels: Vec<ChannelConfig>,

    // ── Audio ─────────────────────────────────────────────────────────────────
    /// CPAL output-stream buffer size in frames (256 / 512 / 1024 / 2048).
    #[serde(default = "default_buffer_size")]
    pub buffer_size: u32,
    /// Wire sample rate in Hz (44100 / 48000 / 96000).
    #[serde(default = "default_sample_rate")]
    pub sample_rate: u32,
    /// Jitter-buffer pre-roll before playback starts (milliseconds).
    #[serde(default = "default_buffer_offset_ms")]
    pub buffer_offset_ms: u32,

    // ── Network ───────────────────────────────────────────────────────────────
    #[serde(default = "default_discovery_port")]
    pub discovery_port: u16,
    #[serde(default = "default_command_port")]
    pub command_port: u16,

    // ── Startup & Behavior ────────────────────────────────────────────────────
    #[serde(default)]
    pub auto_start_streams: bool,
    #[serde(default)]
    pub start_minimized: bool,
    #[serde(default = "default_true")]
    pub tray_on_close: bool,

    // ── Notifications ─────────────────────────────────────────────────────────
    #[serde(default = "default_true")]
    pub notify_peer_events: bool,
    #[serde(default = "default_true")]
    pub notify_channel_errors: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            mode:               "gaming".to_string(),
            gaming_ip:          "192.168.4.225".to_string(),
            streaming_ip:       "192.168.4.224".to_string(),
            gaming_channels:    gaming_defaults(),
            streaming_channels: streaming_defaults(),
            buffer_size:        default_buffer_size(),
            sample_rate:        default_sample_rate(),
            buffer_offset_ms:   default_buffer_offset_ms(),
            discovery_port:     default_discovery_port(),
            command_port:       default_command_port(),
            auto_start_streams: false,
            start_minimized:    false,
            tray_on_close:      true,
            notify_peer_events: true,
            notify_channel_errors: true,
        }
    }
}

fn ch(name: &str, dir: &str, device: &str, port: u16, color: &str, icon: &str) -> ChannelConfig {
    ChannelConfig {
        id:                   uuid::Uuid::new_v4().to_string(),
        name:                 name.to_string(),
        direction:            dir.to_string(),
        device:               device.to_string(),
        port,
        volume:               100,
        color:                color.to_string(),
        icon:                 icon.to_string(),
        enabled:              true,
        custom_icon_base64:   None,
    }
}

fn gaming_defaults() -> Vec<ChannelConfig> {
    vec![
        ch("Game Audio", "OUT", "Game (Elgato Virtual Audio)", 5000, "#ff6b6b", "ti-device-gamepad"),
        ch("Discord",    "OUT", "Discord Audio",               5001, "#5865f2", "ti-brand-discord"),
        ch("Spotify",    "OUT", "Spotify Audio",               5002, "#1db954", "ti-brand-spotify"),
        ch("TTS/Lumia",  "OUT", "TTS Audio",                   5003, "#f59e0b", "ti-robot"),
        ch("OBS Alerts", "IN",  "Corsair HS80 WIRELESS",       5011, "#a855f7", "ti-brand-twitch"),
    ]
}

fn streaming_defaults() -> Vec<ChannelConfig> {
    vec![
        ch("Game Audio", "IN",    "Speakers (Realtek)",   5000, "#ff6b6b", "ti-device-gamepad"),
        ch("Discord",    "IN",    "Speakers (Realtek)",   5001, "#5865f2", "ti-brand-discord"),
        ch("Spotify",    "IN",    "Speakers (Realtek)",   5002, "#1db954", "ti-brand-spotify"),
        ch("TTS/Lumia",  "IN",    "Speakers (Realtek)",   5003, "#f59e0b", "ti-robot"),
        ch("OBS Alerts", "OUT",   "OBS Studio Virtual",   5011, "#a855f7", "ti-brand-twitch"),
    ]
}

impl Config {
    fn path() -> Option<PathBuf> {
        UserDirs::new().map(|d| {
            d.document_dir()
                .unwrap_or(d.home_dir())
                .join("ShadowBridge")
                .join("config.json")
        })
    }

    pub fn load() -> anyhow::Result<Self> {
        let path = Self::path().ok_or_else(|| anyhow::anyhow!("no home dir"))?;
        if !path.exists() { return Ok(Self::default()); }
        let text = std::fs::read_to_string(&path)?;
        Ok(serde_json::from_str(&text)?)
    }

    pub fn save(&self) -> anyhow::Result<()> {
        let path = Self::path().ok_or_else(|| anyhow::anyhow!("no home dir"))?;
        if let Some(p) = path.parent() { std::fs::create_dir_all(p)?; }
        std::fs::write(&path, serde_json::to_string_pretty(self)?)?;
        Ok(())
    }
}
