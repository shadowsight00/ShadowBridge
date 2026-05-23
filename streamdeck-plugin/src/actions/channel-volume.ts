import { action, DialAction, DialRotateEvent, SingletonAction, WillAppearEvent } from '@elgato/streamdeck';
import { shadowBridge } from '../shadowbridge-client';

@action({ UUID: 'com.shadowbridge.app.channel-volume' })
export class ChannelVolume extends SingletonAction {

  onWillAppear(_ev: WillAppearEvent) {
    this.updateDials();
    shadowBridge.on('state', () => this.updateDials());
  }

  async onDialRotate(ev: DialRotateEvent) {
    const settings = await ev.action.getSettings<{ channelId: string }>();
    if (!settings?.channelId || !shadowBridge.connected) return;

    const ch = shadowBridge.state.channels.find(c => c.id === settings.channelId);
    if (!ch) return;

    const newVol = Math.max(0, Math.min(100, ch.volume + ev.payload.ticks * 5));
    ch.volume = newVol;
    shadowBridge.send({ cmd: 'set_volume', id: settings.channelId, value: newVol });
    await ev.action.setFeedback({ value: `${newVol}%`, indicator: { value: newVol } });
  }

  private async updateDials() {
    for (const act of [...this.actions] as DialAction[]) {
      const settings = await act.getSettings<{ channelId: string }>();
      if (!settings?.channelId) continue;
      const ch = shadowBridge.state.channels.find(c => c.id === settings.channelId);
      if (!ch) continue;
      await act.setFeedback({ title: ch.name, value: `${ch.volume}%`, indicator: { value: ch.volume } });
    }
  }
}
