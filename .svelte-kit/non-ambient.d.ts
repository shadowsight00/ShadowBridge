
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	type MatcherParam<M> = M extends (param : string) => param is (infer U extends string) ? U : string;

	export interface AppTypes {
		RouteId(): "/";
		RouteParams(): {
			
		};
		LayoutParams(): {
			"/": Record<string, never>
		};
		Pathname(): "/";
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): "/assets/obs_icon.png" | "/assets/shadowbridge_icon_64.png" | "/assets/shadowbridge_wordmark.png" | "/assets/splash_logo.png" | "/favicon.png" | "/icons/alert.png" | "/icons/bell.png" | "/icons/discord.png" | "/icons/equalizer.png" | "/icons/gamepad.png" | "/icons/googlechrome.png" | "/icons/headphones.png" | "/icons/headset.png" | "/icons/manifest.json" | "/icons/microphone.png" | "/icons/music.png" | "/icons/obsstudio.png" | "/icons/phone.png" | "/icons/podcast.png" | "/icons/speaker.png" | "/icons/spotify.png" | "/icons/steam.png" | "/icons/system.png" | "/icons/teamspeak.png" | "/icons/teamviewer.png" | "/icons/twitch.png" | "/icons/video.png" | "/icons/vlcmediaplayer.png" | "/icons/voice.png" | "/icons/waveform.png" | "/icons/youtube.png" | "/svelte.svg" | "/tauri.svg" | "/vite.svg" | string & {};
	}
}