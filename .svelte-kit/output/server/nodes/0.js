

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export const universal = {
  "ssr": false
};
export const universal_id = "src/routes/+layout.js";
export const imports = ["_app/immutable/nodes/0.BqFO8gmy.js","_app/immutable/chunks/0qX4tfaX.js","_app/immutable/chunks/CrTpzYep.js","_app/immutable/chunks/Dz7iI8PA.js"];
export const stylesheets = ["_app/immutable/assets/0.DMwLvYjA.css"];
export const fonts = [];
