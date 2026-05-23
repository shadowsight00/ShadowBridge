import { action, KeyAction, SingletonAction, WillAppearEvent } from '@elgato/streamdeck';
import { shadowBridge } from '../shadowbridge-client';
import { renderConnectionButton } from '../renderer';

@action({ UUID: 'com.shadowbridge.app.connection-status' })
export class ConnectionStatus extends SingletonAction {

  onWillAppear(_ev: WillAppearEvent) {
    this.updateButtons();
    shadowBridge.on('peer_connected', () => this.updateButtons());
    shadowBridge.on('peer_lost',      () => this.updateButtons());
    shadowBridge.on('connected',      () => this.updateButtons());
    shadowBridge.on('disconnected',   () => this.updateButtons());
    shadowBridge.on('state',          () => this.updateButtons());
  }

  private async updateButtons() {
    for (const act of [...this.actions] as KeyAction[]) {
      if (!shadowBridge.connected) {
        await act.setTitle('APP\nOFFLINE');
        await act.setState(2);
      } else {
        await act.setTitle('');
        await act.setState(shadowBridge.state.peer_connected ? 1 : 0);
        const img = renderConnectionButton(
          shadowBridge.state.peer_connected,
          shadowBridge.state.peer_ip,
        );
        await act.setImage(img);
      }
    }
  }
}
