import {
  action,
  KeyDownEvent,
  SingletonAction,
  WillAppearEvent,
  DidReceiveSettingsEvent
} from '@elgato/streamdeck';
import { shadowBridge } from '../shadowbridge-client';
import { renderStripHeader, renderFaderFull } from '../renderer';

type StripSettings = {
  channelId: string;
  slot: number;  // 0 = header, 1 = upper fader, 2 = lower fader
};

@action({ UUID: 'com.shadowbridge.app.channel-strip' })
export class ChannelStrip extends SingletonAction {
  private levelMap = new Map<string, number>();
  private muteMap  = new Map<string, boolean>();
  private meterTimer: NodeJS.Timeout | null = null;
  private listenersRegistered = false;

  async onWillAppear(ev: WillAppearEvent<{ channelId: string; slot: number }>) {
    await this.renderAction(ev.action, ev.payload.settings as StripSettings);

    // Register listeners only once — onWillAppear fires once per button,
    // so without this guard we'd accumulate duplicate handlers on every button.
    if (!this.listenersRegistered) {
      this.listenersRegistered = true;

      shadowBridge.on('state',              () => this.updateAll().catch(() => {}));
      shadowBridge.on('channel_toggled',    () => this.updateAll().catch(() => {}));
      shadowBridge.on('channel_appearance', () => this.updateAll().catch(() => {}));
      shadowBridge.on('channel_volume',     (id: string, vol: number) => { console.error('[SD] channel_volume event id=' + id + ' vol=' + vol); this.updateAll().catch(() => {}); });
      shadowBridge.on('connected',          () => this.updateAll().catch(() => {}));
      shadowBridge.on('disconnected',       () => this.updateAll().catch(() => {}));

      shadowBridge.on('channel_level', (id: string, level: number) => {
        this.levelMap.set(id, level);
        if (!this.meterTimer) {
          this.meterTimer = setTimeout(() => {
            this.meterTimer = null;
            this.updateAll().catch(() => {});
          }, 80);
        }
      });
    }
  }

  async onDidReceiveSettings(ev: DidReceiveSettingsEvent<{ channelId: string; slot: number }>) {
    await this.renderAction(ev.action, ev.payload.settings as StripSettings);
  }

  async onKeyDown(ev: KeyDownEvent<{ channelId: string; slot: number }>) {
    const { channelId, slot } = ev.payload.settings;
    if (!channelId || !shadowBridge.connected) return;

    const ch = shadowBridge.state.channels.find(c => c.id === channelId);

    if (slot === 0) {
      // Header — toggle channel on/off with optimistic local update
      if (ch) ch.enabled = !ch.enabled;
      shadowBridge.send({ cmd: 'toggle_channel', id: channelId });

    } else if (slot === 1) {
      // Upper fader — volume up 5%
      if (!ch) return;
      const newVol = Math.min(100, (ch.volume ?? 100) + 5);
      ch.volume = newVol;
      shadowBridge.send({ cmd: 'set_volume', id: channelId, value: newVol });

    } else if (slot === 2) {
      // Lower fader — volume down 5%; at 0 toggles mute
      if (!ch) return;
      if ((ch.volume ?? 100) === 0) {
        const newMute = !(this.muteMap.get(channelId) ?? false);
        this.muteMap.set(channelId, newMute);
        shadowBridge.send({ cmd: newMute ? 'mute_channel' : 'unmute_channel', id: channelId });
      } else {
        const newVol = Math.max(0, (ch.volume ?? 100) - 5);
        ch.volume = newVol;
        shadowBridge.send({ cmd: 'set_volume', id: channelId, value: newVol });
      }
    }

    // Render immediately with optimistic state, then let server confirm
    await this.updateAll().catch(() => {});
    shadowBridge.send({ cmd: 'get_state' });
  }

  private async renderAction(action: any, settings: StripSettings) {
    const { channelId, slot } = settings;
    if (!channelId) {
      await action.setTitle(slot === 0 ? 'SET\nCHANNEL' : '');
      return;
    }

    const ch = shadowBridge.state.channels.find(c => c.id === channelId);
    if (!ch) {
      await action.setTitle(slot === 0 ? 'NOT\nFOUND' : '');
      return;
    }

    const level = this.levelMap.get(channelId) ?? 0;
    const muted = this.muteMap.get(channelId) ?? false;

    try {
      await action.setTitle('');
      if (slot === 0) {
        const img = await renderStripHeader({ ...ch, level });
        await action.setImage(img);
      } else {
        const { top, bottom } = renderFaderFull({ ...ch, level }, muted);
        await action.setImage(slot === 1 ? top : bottom);
      }
    } catch (err) {
      console.error('ChannelStrip render error:', err);
      await action.setTitle(ch.name);
    }
  }

  private async updateAll() {
    const groups = new Map<string, Array<{ action: any; settings: StripSettings }>>();

    for (const act of [...this.actions]) {
      let settings: { channelId: string; slot: number } | undefined;
      try {
        settings = await act.getSettings<{ channelId: string; slot: number }>();
      } catch { continue; }
      if (!settings?.channelId) continue;
      const key = settings.channelId;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push({ action: act, settings: settings as StripSettings });
    }

    for (const [channelId, items] of groups) {
      const ch    = shadowBridge.state.channels.find(c => c.id === channelId);
      const level = this.levelMap.get(channelId) ?? 0;
      const muted = this.muteMap.get(channelId) ?? false;

      const faderPair = ch ? renderFaderFull({ ...ch, level }, muted) : null;

      for (const { action, settings } of items) {
        try {
          if (!ch) { await action.setTitle('NOT\nFOUND'); continue; }
          await action.setTitle('');
          if (settings.slot === 0) {
            const img = await renderStripHeader({ ...ch, level });
            await action.setImage(img);
          } else if (faderPair) {
            await action.setImage(settings.slot === 1 ? faderPair.top : faderPair.bottom);
          }
        } catch { /* ignore timeout/render errors */ }
      }
    }
  }
}
