export const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set(["assets/obs_icon.png","assets/shadowbridge_icon_64.png","assets/shadowbridge_wordmark.png","assets/splash_logo.png","favicon.png","icons/alert.png","icons/bell.png","icons/discord.png","icons/equalizer.png","icons/gamepad.png","icons/googlechrome.png","icons/headphones.png","icons/headset.png","icons/manifest.json","icons/microphone.png","icons/music.png","icons/obsstudio.png","icons/phone.png","icons/podcast.png","icons/speaker.png","icons/spotify.png","icons/steam.png","icons/system.png","icons/teamspeak.png","icons/teamviewer.png","icons/twitch.png","icons/video.png","icons/vlcmediaplayer.png","icons/voice.png","icons/waveform.png","icons/youtube.png","svelte.svg","tauri.svg","vite.svg"]),
	mimeTypes: {".png":"image/png",".json":"application/json",".svg":"image/svg+xml"},
	_: {
		client: {start:"_app/immutable/entry/start.u9m9s-pH.js",app:"_app/immutable/entry/app.CWQapK5W.js",imports:["_app/immutable/entry/start.u9m9s-pH.js","_app/immutable/chunks/V0cPHNB5.js","_app/immutable/chunks/CrTpzYep.js","_app/immutable/entry/app.CWQapK5W.js","_app/immutable/chunks/CrTpzYep.js","_app/immutable/chunks/D7zUyTAP.js","_app/immutable/chunks/0qX4tfaX.js","_app/immutable/chunks/Dz7iI8PA.js","_app/immutable/chunks/5eZNyhs1.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js')),
			__memo(() => import('./nodes/2.js'))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/",
				pattern: /^\/$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();
