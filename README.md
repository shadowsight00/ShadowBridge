# ShadowBridge

**Audio routing software built by a streamer, for streamers.**

ShadowBridge is a Windows application designed for dual PC streaming setups. It automatically routes audio from your gaming PC to your streaming PC over your local network — no complicated DAW software, no expensive hardware mixers required. Just open it on both machines and hit Start.

---

## Features

### Core Audio Routing
- **One-click start/stop** — clicking Start All on either PC starts both simultaneously
- **Auto peer discovery** — both PCs find each other automatically on your local network, no manual IP configuration required
- **Per-channel audio routing** — route game audio, Discord, Spotify, alerts, and more as individual channels
- **Per-app audio capture** — capture audio directly from a specific running application without needing a virtual audio device
- **Mic routing** — MIC-IN and MIC-OUT channel types for flexible microphone routing between PCs
- **Per-channel volume control** — adjust levels independently for each channel
- **Per-channel enable/disable** — toggle individual channels without stopping everything
- **Live level meters** — see audio activity on every channel in real time
- **Auto-reconnect** — dropped channels reconnect automatically without restarting

### UI & Customization
- **Mixer-style channel strips** — vertical fader strips with live level meters, styled like a professional audio mixer
- **Per-channel color** — assign any color to each channel, reflected across the entire strip
- **Per-channel icons** — choose from preset icons, upload a custom image, or use the app's own icon for app-capture channels automatically
- **Right-click context menu** — rename, recolor, change icon, toggle, or delete channels from a single menu
- **HUD-style interface** — dark teal theme with cyan accents, scanline overlay, and corner bracket decorations
- **Resizable and fullscreen** — scales from compact to fullscreen
- **System tray support** — minimizes to tray, stays out of your way while you stream
- **Single instance enforcement** — only one copy of ShadowBridge runs at a time

### Stream Deck Integration
- **Start/Stop button** — start and stop all streams from your deck with live status (LIVE/OFF/OFFLINE)
- **Channel toggle buttons** — enable/disable individual channels from your deck
- **Fader controls** — two-button vertical fader per channel with live level meter and real-time volume control
- **Connection status button** — shows whether both PCs are connected
- **Visual sync** — Stream Deck buttons match your channel colors and icons automatically

### Settings & Automation
- **Audio buffer size** — tune latency vs stability for your network
- **Sample rate selection** — 44100 or 48000 Hz
- **Custom discovery and command ports** — avoid conflicts with other software
- **Launch on Windows startup** — start automatically with Windows
- **Auto-start streams** — start streaming automatically when the other PC is detected
- **Start minimized** — launch straight to the system tray
- **Desktop notifications** — get notified when the peer connects, disconnects, or a channel errors

---

## Requirements

- Windows 10 or Windows 11 (both PCs)
- Virtual audio devices installed on both computers
  - **WaveLink** (recommended — works out of the box with Elgato hardware)
  - Voicemeeter or other virtual audio software also works
- Both PCs connected to the same local network
- Stream Deck software (optional, for Stream Deck integration)

---

## Installation

1. Download the latest `ShadowBridge_Setup.exe` from the [Releases](https://github.com/shadowsight00/ShadowBridge/releases) page
2. Run the installer on **both** your gaming PC and your streaming PC
3. Launch ShadowBridge on both machines
4. The app will automatically detect which PC it's on based on your network IP
5. Click **Start All** on either PC — both will start simultaneously

For the Stream Deck plugin, download `com.shadowsight00.shadowbridge.streamDeckPlugin` from the Releases page and double-click to install.

---

## Setup Guide

### First Launch

ShadowBridge will attempt to detect whether it's running on your gaming PC or streaming PC based on your network IP. You can manually switch modes using the mode pill button in the top bar.

### Configuring Channels

Channels are grouped into three sections:

- **Outgoing** — capture audio from a virtual device or running app on the gaming PC and send it to the streaming PC
- **Incoming** — receive audio from the gaming PC and play it to a virtual device on the streaming PC
- **Mic Inputs** — route microphone audio between PCs

To configure a channel:
1. Click **Select Source** at the bottom of the channel strip to choose a device or application
2. Right-click the strip to rename, recolor, or change the icon
3. Click the direction badge to change between OUT, IN, MIC-IN, and MIC-OUT
4. Use the **On/Off** toggle to enable or disable individual channels
5. Drag the fader handle to adjust volume

### Per-App Audio Capture

To capture audio directly from a running application:
1. Add a new channel in the Outgoing section
2. Click **Select Source** at the bottom of the strip
3. Switch to the **Application Sources** tab
4. Select the running application — the channel direction switches to APP automatically and the app icon is applied

### Mic Routing

To route your microphone from your streaming PC to your gaming PC for Discord:

1. On the **streaming PC** — add a channel, set direction to **MIC-IN**, select your microphone as the source
2. On the **gaming PC** — the matching channel should appear with direction **MIC-OUT**, select your WaveLink output device
3. In Discord on your gaming PC, set WaveLink as your microphone input
4. Hit Start All — mic audio routes automatically

### Stream Deck Setup

1. Install the plugin from the Releases page
2. Open Stream Deck software — ShadowBridge actions appear in the right panel
3. Drag **Start/Stop**, **Channel Toggle**, **Fader**, or **Connection Status** to your buttons
4. Configure which channel each button controls in the property inspector
5. Colors and icons sync automatically from the app

### Settings

Open **Settings** from the top bar to configure:
- Gaming PC and Streaming PC IP addresses
- Audio buffer size and sample rate
- Discovery and command ports
- Startup and automation behavior
- Desktop notification preferences

---

## Roadmap

- Mobile companion app (Android APK)
- Web companion dashboard
- Channel presets and scene switching
- Volume normalization per channel
- Elgato Marketplace listing for Stream Deck plugin (currently in review)

---

## Contributing

Pull requests are welcome. If you find a bug or have a feature request, please open an issue on the [Issues](https://github.com/shadowsight00/ShadowBridge/issues) page and include your log file from `Documents\ShadowBridge\logs`.

---

## License

This project is provided as-is for personal and streaming use. See [LICENSE](LICENSE) for details.

---

*Built by a streamer, for streamers. If ShadowBridge has made your setup simpler, consider sharing it with your community.*
