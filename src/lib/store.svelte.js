import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { sendNotification } from '@tauri-apps/plugin-notification';

/**
 * @typedef {{
 *   id: string, name: string, direction: string,
 *   device: string, port: number, volume: number,
 *   color: string, icon: string, enabled: boolean,
 *   custom_icon_base64?: string | null
 * }} ChannelConfig
 */

export let config = $state({
  mode: 'gaming',
  gaming_ip: '192.168.4.225',
  streaming_ip: '192.168.4.224',
  gaming_channels: /** @type {ChannelConfig[]} */ ([]),
  streaming_channels: /** @type {ChannelConfig[]} */ ([]),
  // Audio
  buffer_size: 1024,
  sample_rate: 48000,
  buffer_offset_ms: 20,
  // Network
  discovery_port: 5999,
  command_port: 8765,
  // Startup & Behavior
  auto_start_streams: false,
  start_minimized: false,
  tray_on_close: true,
  // Notifications
  notify_peer_events: true,
  notify_channel_errors: true,
});

export let engineRunning  = $state({ value: false });
export let peerStatus     = $state({ connected: false, ip: /** @type {string|null} */ (null), mode: /** @type {string|null} */ (null) });
export let channelLevels  = $state(/** @type {Record<string,number>} */ ({}));
export let channelStatuses= $state(/** @type {Record<string,string>} */ ({}));
export let engineError    = $state({ message: '', ts: 0, visible: false });

export function clearEngineError() { engineError.visible = false; }

export async function loadConfig() {
  const cfg = await invoke('load_config');
  config.mode                 = cfg.mode                 ?? 'gaming';
  config.gaming_ip            = cfg.gaming_ip            ?? '';
  config.streaming_ip         = cfg.streaming_ip         ?? '';
  config.gaming_channels      = cfg.gaming_channels      ?? [];
  config.streaming_channels   = cfg.streaming_channels   ?? [];
  config.buffer_size          = cfg.buffer_size          ?? 1024;
  config.sample_rate          = cfg.sample_rate          ?? 48000;
  config.buffer_offset_ms     = cfg.buffer_offset_ms     ?? 20;
  config.discovery_port       = cfg.discovery_port       ?? 5999;
  config.command_port         = cfg.command_port         ?? 8765;
  config.auto_start_streams   = cfg.auto_start_streams   ?? false;
  config.start_minimized      = cfg.start_minimized      ?? false;
  config.tray_on_close        = cfg.tray_on_close        ?? true;
  config.notify_peer_events   = cfg.notify_peer_events   ?? true;
  config.notify_channel_errors= cfg.notify_channel_errors?? true;
}

export async function saveConfig() {
  await invoke('save_config', { config: { ...config } });
}

export async function startMonitoring() {
  const channels = config.mode === 'gaming' ? config.gaming_channels : config.streaming_channels;
  await invoke('start_monitoring', { channels });
}

export async function stopMonitoring() {
  await invoke('stop_monitoring');
}

export async function startEngine() {
  const channels = config.mode === 'gaming' ? config.gaming_channels : config.streaming_channels;
  const destIp   = config.mode === 'gaming' ? config.streaming_ip     : config.gaming_ip;
  await invoke('start_engine', { channels, destIp, mode: config.mode });
  engineRunning.value = true;
}

export async function stopEngine() {
  await invoke('stop_engine');
  engineRunning.value = false;
}

export async function setChannelVolume(channelId, volume) {
  await invoke('set_channel_volume', { channelId, volume });
}

export async function restartEngineChannel(channel) {
  await invoke('restart_engine_channel', { channel: { ...channel } });
}

export async function sendPeerCommand(peerIp, cmd) {
  await invoke('send_peer_command', { peerIp, cmd });
}

export async function setupListeners() {
  const u1 = await listen('channel-status', (e) => {
    channelStatuses[e.payload.id] = e.payload.status;
  });
  const u2 = await listen('channel-level', (e) => {
    channelLevels[e.payload.id] = e.payload.level;
  });
  const u3 = await listen('peer-found', (e) => {
    peerStatus.connected = true;
    peerStatus.ip   = e.payload.ip;
    peerStatus.mode = e.payload.mode;
    if (config.notify_peer_events) {
      sendNotification({ title: 'ShadowBridge', body: `Peer connected — ${e.payload.ip}` }).catch(() => {});
    }
  });
  const u4 = await listen('peer-lost', (e) => {
    peerStatus.connected = false;
    peerStatus.ip   = null;
    peerStatus.mode = null;
    if (config.notify_peer_events) {
      sendNotification({ title: 'ShadowBridge', body: 'Peer disconnected' }).catch(() => {});
    }
  });
  const u5a = await listen('engine-started-tray', () => { engineRunning.value = true; });
  const u5b = await listen('engine-stopped-tray',  () => { engineRunning.value = false; });
  const u6 = await listen('channel-volume', (e) => {
    const channels = config.mode === 'gaming' ? config.gaming_channels : config.streaming_channels;
    const ch = channels.find(c => c.id === e.payload.id);
    if (ch) ch.volume = e.payload.volume;
  });
  const u7 = await listen('channel-toggled', (e) => {
    const channels = config.mode === 'gaming' ? config.gaming_channels : config.streaming_channels;
    const ch = channels.find(c => c.id === e.payload.id);
    if (ch) ch.enabled = e.payload.enabled;
  });
  const u5 = await listen('engine-error', (e) => {
    engineError.message = e.payload.message;
    engineError.ts      = Date.now();
    engineError.visible = true;
    if (config.notify_channel_errors) {
      sendNotification({ title: 'ShadowBridge — Engine Error', body: e.payload.message }).catch(() => {});
    }
    setTimeout(() => { if (Date.now() - engineError.ts >= 5000) engineError.visible = false; }, 5100);
  });
  return () => { u1(); u2(); u3(); u4(); u5a(); u5b(); u6(); u7(); u5(); };
}
