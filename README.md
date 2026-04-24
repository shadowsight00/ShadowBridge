# ShadowBridge

**Audio routing software built by a streamer, for streamers.**

ShadowBridge is a lightweight Windows application designed for dual PC streaming setups. It automatically routes audio from your gaming PC to your streaming PC over your local network — no complicated DAW software, no expensive hardware mixers required. Just open it on both machines and hit Start.

---

## Features

- **One-click start/stop** : clicking Start All on either PC starts both simultaneously
- **Auto peer discovery** : both PCs find each other automatically on your local network, no manual IP configuration required
- **Per-channel audio routing** : route game audio, Discord, Spotify, music, alerts, and more as individual channels
- **Mic routing** : send your microphone audio back to your gaming PC for use in Discord
- **Per-channel volume control** : adjust levels independently for each channel
- **Per-channel enable/disable** : toggle individual channels without stopping everything
- **Live level meters** : see audio activity on every channel in real time
- **System tray support** : minimizes to tray, stays out of your way while you stream
- **Dark and light mode** : switch themes from the settings menu
- **Resizable window** : scale from compact to fullscreen
- **Auto-reconnect** : dropped channels reconnect automatically without restarting
- **Persistent config** : your channel layout and settings are saved between sessions

---

## Requirements

- Windows 10 or Windows 11 (both PCs)
- Virtual audio devices installed on both computers
  - **WaveLink** (recommended. Works out of the box with Elgato hardware)
  - Other virtual audio software such as Voicemeeter should also work
- Both PCs connected to the same local network

---

## Installation

1. Download the latest `ShadowBridge_Setup.exe` from the [Releases](https://github.com/shadowsight00/ShadowBridge/releases) page
2. Run the installer on **both** your gaming PC and your streaming PC
3. Launch ShadowBridge on both machines
4. The app will automatically detect which PC it's on and configure itself accordingly
5. Click **Start All** on either PC. Both will start simultaneously

---

## Setup Guide

### First Launch

When you open ShadowBridge for the first time, it will attempt to detect whether it's running on your gaming PC or streaming PC based on your network IP. You can manually switch modes using the mode button in the top bar.

### Configuring Channels

Each channel represents one audio stream between your two PCs:

- **Outgoing channels** : capture audio from a virtual audio device on the gaming PC and send it to the streaming PC
- **Incoming channels** : receive audio from the gaming PC and play it to a virtual audio device on the streaming PC
- **Mic channels** : capture microphone input on the streaming PC and send it back to the gaming PC

To set up a channel:
1. Click **Change** on the channel to select your virtual audio device
2. Set the channel name to something recognizable (e.g. Game Audio, Discord, Spotify)
3. Use the direction button to toggle between Out, In, and Mic
4. Use the On/Off toggle to enable or disable individual channels

### Mic Routing

To route your microphone from your streaming PC to your gaming PC for Discord:

1. On the gaming PC, add a new channel and set its direction to **Mic**
2. Select your WaveLink mic input device (e.g. `Mic In (Elgato Wave:XLR)`) as the output device
3. In Discord on your gaming PC, set WaveLink (e.g. `Mic SPC Audio`) as your input device
4. Hit Start All. Your mic audio will now route through to Discord automatically

### Settings

Open the **Settings** panel from the top bar to configure:
- Gaming PC and Streaming PC IP addresses (if auto-detection doesn't work)
- Dark / light mode

---

## Roadmap

- Per-app audio capture (WASAPI) : Route audio directly from specific applications without needing virtual audio devices on the gaming PC
- Channel grouping and presets
- Auto-launch on Windows startup
- Volume normalization per channel
- Mobile companion app for remote monitoring

---

## Contributing

Pull requests are welcome. If you find a bug or have a feature request, please open an issue on the [Issues](https://github.com/shadowsight00/ShadowBridge/issues) page.

---

## License

This project is provided as-is for personal and streaming use. See [LICENSE](LICENSE) for details.

---

*Built by a streamer, for streamers. If ShadowBridge has made your setup simpler, consider sharing it with your community.*
