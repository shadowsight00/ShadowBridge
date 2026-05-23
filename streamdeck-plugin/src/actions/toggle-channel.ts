import {
  action,
  KeyDownEvent,
  SingletonAction,
  WillAppearEvent,
  DidReceiveSettingsEvent
} from '@elgato/streamdeck';
import { shadowBridge } from '../shadowbridge-client';
import { renderChannelStrip } from '../renderer';

@action({ UUID: 'com.shadowbridge.app.toggle-channel' })
export class ToggleChannel extends SingletonAction {
  private levelMap = new Map<string, number>();

  async onWillAppear(ev: WillAppearEvent<{ channelId: string }>) {
    const settings = ev.payload.settings;
    if (settings?.channelId) {
      await this.renderForAction(ev.action, settings.channelId);
    }

    shadowBridge.on('state', () => this.updateAllButtons());
    shadowBridge.on('channel_toggled', () => this.updateAllButtons());
    shadowBridge.on('channel_appearance', () => this.updateAllButtons());
    shadowBridge.on('connected', () => this.updateAllButtons());

    shadowBridge.on('channel_level', (id: string, level: number) => {
      this.levelMap.set(id, level);
    });
  }

  async onDidReceiveSettings(ev: DidReceiveSettingsEvent<{ channelId: string }>) {
    const channelId = ev.payload.settings?.channelId;
    if (!channelId) return;
    await this.renderForAction(ev.action, channelId);
  }

  async onKeyDown(ev: KeyDownEvent<{ channelId: string }>) {
    const channelId = ev.payload.settings?.channelId;
    if (!channelId || !shadowBridge.connected) return;
    shadowBridge.send({ cmd: 'toggle_channel', id: channelId });
  }

  private async renderForAction(action: any, channelId: string) {
    const ch = shadowBridge.state.channels.find(c => c.id === channelId);
    if (!ch) {
      await action.setTitle('NO\nCHANNEL');
      return;
    }
    try {
      const level = this.levelMap.get(channelId) ?? 0;
      const img = await renderChannelStrip({ ...ch, level });
      await action.setTitle('');
      await action.setImage(img);
    } catch (err) {
      console.error('renderChannelStrip failed:', err);
      await action.setTitle(ch.name);
    }
  }

  private async updateAllButtons() {
    for (const action of [...this.actions]) {
      const settings = await action.getSettings<{ channelId: string }>();
      if (settings?.channelId) {
        await this.renderForAction(action, settings.channelId);
      }
    }
  }
}
