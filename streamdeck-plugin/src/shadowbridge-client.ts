import WebSocket from 'ws';
import { EventEmitter } from 'events';

export class ShadowBridgeClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private readonly url = 'ws://localhost:8765';
  public connected = false;
  public state: ShadowBridgeState = {
    streaming: false,
    peer_connected: false,
    peer_ip: null,
    mode: 'gaming',
    channels: []
  };

  connect() {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.on('open', () => {
        this.connected = true;
        this.emit('connected');
        this.send({ cmd: 'get_state' });
      });

      this.ws.on('message', (data: WebSocket.RawData) => {
        try {
          const msg = JSON.parse(data.toString());
          this.handleMessage(msg);
        } catch {}
      });

      this.ws.on('close', () => {
        this.connected = false;
        this.emit('disconnected');
        this.scheduleReconnect();
      });

      this.ws.on('error', () => {
        this.connected = false;
        this.scheduleReconnect();
      });

    } catch {
      this.scheduleReconnect();
    }
  }

  private handleMessage(msg: Record<string, unknown>) {
    if (msg['event'] === 'state') {
      this.state = msg as unknown as ShadowBridgeState;
      this.emit('state', this.state);
    } else if (msg['event'] === 'streaming_started') {
      this.state.streaming = true;
      this.emit('streaming_started');
    } else if (msg['event'] === 'streaming_stopped') {
      this.state.streaming = false;
      this.emit('streaming_stopped');
    } else if (msg['event'] === 'peer_connected') {
      this.state.peer_connected = true;
      this.state.peer_ip = msg['ip'] as string;
      this.emit('peer_connected', msg['ip']);
    } else if (msg['event'] === 'peer_lost') {
      this.state.peer_connected = false;
      this.state.peer_ip = null;
      this.emit('peer_lost');
    } else if (msg['event'] === 'channel_toggled') {
      const ch = this.state.channels.find(c => c.id === msg['id']);
      if (ch) {
        ch.enabled = msg['enabled'] as boolean;
        if (msg['name'])  ch.name  = msg['name']  as string;
        if (msg['color']) ch.color = msg['color'] as string;
        if (msg['icon'])  ch.icon  = msg['icon']  as string;
      }
      this.emit('channel_toggled', msg['id'], msg['enabled']);
    } else if (msg['event'] === 'channel_appearance') {
      const ch = this.state.channels.find(c => c.id === msg['id']);
      if (ch) {
        ch.name             = msg['name']             as string;
        ch.color            = msg['color']            as string;
        ch.icon             = msg['icon']             as string;
        ch.iconId           = msg['iconId']           as string | null;
        ch.customIconBase64 = msg['customIconBase64'] as string | null;
      }
      this.emit('channel_appearance', msg['id']);
    } else if (msg['event'] === 'channel_volume') {
      const ch = this.state.channels.find(c => c.id === msg['id']);
      console.error('[SB] channel_volume received id=' + msg['id'] + ' volume=' + msg['volume'] + ' ch_found=' + !!ch);
      if (ch) ch.volume = msg['volume'] as number;
      this.emit('channel_volume', msg['id'], msg['volume']);
    } else if (msg['event'] === 'channel_level') {
      this.emit('channel_level', msg['id'], msg['level']);
    } else if (msg['event'] === 'channel_status') {
      const ch = this.state.channels.find(c => c.id === msg['id']);
      if (ch) ch.status = msg['status'] as string;
      this.emit('channel_status', msg['id'], msg['status']);
    }
    this.emit('any', msg);
  }

  send(data: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 3000);
  }
}

export interface ShadowBridgeState {
  streaming: boolean;
  peer_connected: boolean;
  peer_ip: string | null;
  mode: string;
  channels: ChannelState[];
}

export interface ChannelState {
  id: string;
  name: string;
  color: string;
  icon: string;
  iconId: string | null;
  customIconBase64: string | null;
  direction: string;
  enabled: boolean;
  volume: number;
  status: string;
}

export const shadowBridge = new ShadowBridgeClient();
