import { action, KeyAction, KeyDownEvent, SingletonAction, WillAppearEvent } from '@elgato/streamdeck';
import { shadowBridge } from '../shadowbridge-client';
import { renderStartButton } from '../renderer';

@action({ UUID: 'com.shadowbridge.app.toggle-streaming' })
export class ToggleStreaming extends SingletonAction {

  onWillAppear(_ev: WillAppearEvent) {
    this.updateButton();
    shadowBridge.on('streaming_started', () => this.updateButton());
    shadowBridge.on('streaming_stopped', () => this.updateButton());
    shadowBridge.on('connected',         () => this.updateButton());
    shadowBridge.on('disconnected',      () => this.updateButton());
    shadowBridge.on('state',             () => this.updateButton());
  }

  async onKeyDown(_ev: KeyDownEvent) {
    if (!shadowBridge.connected) return;
    if (shadowBridge.state.streaming) {
      shadowBridge.state.streaming = false;
      shadowBridge.send({ cmd: 'stop_all' });
    } else {
      shadowBridge.state.streaming = true;
      shadowBridge.send({ cmd: 'start_all' });
    }
    await this.updateButton();
    // Request fresh state so server-side truth overrides optimistic update
    shadowBridge.send({ cmd: 'get_state' });
  }

  private async updateButton() {
    for (const act of [...this.actions] as KeyAction[]) {
      if (!shadowBridge.connected) {
        await act.setTitle('OFFLINE');
        await act.setState(2);
      } else {
        await act.setTitle('');
        await act.setState(shadowBridge.state.streaming ? 1 : 0);
        const img = renderStartButton(shadowBridge.state.streaming);
        await act.setImage(img);
      }
    }
  }
}
