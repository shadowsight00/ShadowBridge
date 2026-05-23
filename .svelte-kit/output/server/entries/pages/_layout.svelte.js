import "clsx";
function Splash($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    $$renderer2.push(`<div class="splash svelte-1js76h4"><img src="/assets/splash_logo.png" alt="ShadowBridge" class="logo svelte-1js76h4"/> <div class="bar-wrap svelte-1js76h4"><div class="bar svelte-1js76h4"></div></div></div>`);
  });
}
function _layout($$renderer, $$props) {
  let { children } = $$props;
  {
    $$renderer.push("<!--[0-->");
    Splash($$renderer);
  }
  $$renderer.push(`<!--]--> `);
  children($$renderer);
  $$renderer.push(`<!---->`);
}
export {
  _layout as default
};
