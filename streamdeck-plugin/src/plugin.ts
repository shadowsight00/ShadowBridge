import { streamDeck } from '@elgato/streamdeck';
import { ToggleStreaming } from './actions/toggle-streaming';
import { ToggleChannel } from './actions/toggle-channel';
import { ConnectionStatus } from './actions/connection-status';
import { ChannelVolume } from './actions/channel-volume';
import { ChannelStrip } from './actions/channel-strip';
import { shadowBridge } from './shadowbridge-client';

shadowBridge.connect();

streamDeck.actions.registerAction(new ToggleStreaming());
streamDeck.actions.registerAction(new ToggleChannel());
streamDeck.actions.registerAction(new ConnectionStatus());
streamDeck.actions.registerAction(new ChannelVolume());
streamDeck.actions.registerAction(new ChannelStrip());

streamDeck.connect();
