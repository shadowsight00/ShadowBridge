import { Q as ensure_array_like, K as attr_style, a8 as stringify, P as derived, G as attr, V as escape_html, J as attr_class } from "../../chunks/renderer.js";
import { invoke } from "@tauri-apps/api/core";
import "@tauri-apps/api/event";
import "clsx";
import "@tauri-apps/plugin-notification";
function html(value) {
  var html2 = String(value ?? "");
  var open = "<!---->";
  return open + html2 + "<!---->";
}
function LevelMeter($$renderer, $$props) {
  let { level = 0, color = "#22c55e" } = $$props;
  const NUM = 60;
  const DIM = "#21262d";
  const numActive = derived(() => Math.round(Math.max(0, Math.min(1, level)) * NUM));
  function segColor(i) {
    if (i >= NUM - 2) return "#ef4444";
    if (i >= NUM - 4) return "#eab308";
    return color;
  }
  $$renderer.push(`<div class="meter svelte-71nkj0"><!--[-->`);
  const each_array = ensure_array_like(Array(NUM));
  for (let i = 0, $$length = each_array.length; i < $$length; i++) {
    each_array[i];
    $$renderer.push(`<div class="seg svelte-71nkj0"${attr_style(`background:${stringify(i < numActive() ? segColor(i) : DIM)}`)}></div>`);
  }
  $$renderer.push(`<!--]--></div>`);
}
const ICONS = {
  "ti-device-gamepad-2": '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 12h4m-2-2v4"/><path d="M15 11h.01M17 11h.01M15 13h.01M17 13h.01"/>',
  "ti-device-gamepad": '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 12h4m-2-2v4M15 11h.01M18 11h.01"/>',
  "ti-brand-discord": '<path d="M14.983 3l.123.006c2.014.214 3.527.672 4.966 1.673a1 1 0 0 1 .371.488c1.876 5.315 2.373 9.987 1.451 12.28l-.032.073a4.82 4.82 0 0 1-1.544 1.99 3.04 3.04 0 0 1-1.958.49 1.004 1.004 0 0 1-.8-.595l-.723-1.718a14.516 14.516 0 0 1-5.837 0l-.724 1.72a1 1 0 0 1-.8.593 3.04 3.04 0 0 1-1.957-.49 4.82 4.82 0 0 1-1.544-1.99L6.945 17.5c-.922-2.293-.425-6.965 1.451-12.28a1 1 0 0 1 .371-.488C10.207 3.672 11.72 3.214 13.734 3l.249.006zM9.5 11.5a1 1 0 1 0 2 0 1 1 0 0 0-2 0zm5 0a1 1 0 1 0 2 0 1 1 0 0 0-2 0z" fill="currentColor" stroke="none"/>',
  "ti-brand-spotify": '<circle cx="12" cy="12" r="9"/><path d="M8 15.5a9.818 9.818 0 0 1 8 0M7.5 11.5a13.09 13.09 0 0 1 9 0M8.5 7.5a15 15 0 0 1 7 0"/>',
  "ti-robot": '<rect x="6" y="4" width="12" height="12" rx="2"/><circle cx="9.5" cy="9.5" r="1.5" fill="currentColor" stroke="none"/><circle cx="14.5" cy="9.5" r="1.5" fill="currentColor" stroke="none"/><path d="M10 13h4M12 4V2m-6 18 2-3m8 3-2-3"/>',
  "ti-brand-twitch": '<path d="M21 2H3v16l4-4h14V2zm-9 5v5m-4.5-5v5"/>',
  "ti-microphone": '<rect x="9" y="2" width="6" height="11" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 19v3M9 22h6"/>',
  "ti-headphones": '<path d="M3 14a9 9 0 0 1 18 0"/><path d="M3 14v4a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2H3zm18 0v4a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2h4z"/>',
  "ti-headset": '<path d="M4 14a8 8 0 0 1 16 0"/><path d="M4 14v2a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-2H4zm16 0v2a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-2h5z"/>',
  "ti-volume": '<path d="M15 8a5 5 0 0 1 0 8"/><path d="M11 5 6 9H3v6h3l5 4V5z"/>',
  "ti-volume-off": '<path d="M11 5 6 9H3v6h3l5 4V5zm6 0 4 4m0-4-4 4"/>',
  "ti-music": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  "ti-radio": '<circle cx="12" cy="12" r="3"/><path d="M4.93 4.93a10 10 0 0 0 0 14.14M19.07 4.93a10 10 0 0 1 0 14.14M7.76 7.76a6 6 0 0 0 0 8.48M16.24 7.76a6 6 0 0 1 0 8.48"/>',
  "ti-broadcast": '<circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/><path d="M7.05 7.05a7 7 0 0 0 0 9.9M16.95 7.05a7 7 0 0 1 0 9.9M4.22 4.22a11 11 0 0 0 0 15.56M19.78 4.22a11 11 0 0 1 0 15.56"/>',
  "ti-waveform": '<path d="M2 12h3l2.5-7 3 14 3-10 2.5 7H22"/>',
  "ti-speaker": '<path d="M15 8a5 5 0 0 1 0 8M5 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2l5 4V4L5 8z"/>',
  "ti-device-laptop": '<rect x="3" y="4" width="18" height="12" rx="1"/><path d="M1 20h22"/>',
  "ti-player-play": '<path d="M7 4v16l13-8-13-8z"/>',
  "ti-player-stop": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
  "ti-adjustments-horizontal": '<circle cx="14" cy="6" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="14" cy="18" r="2"/><path d="M4 6h8m4 0h4M4 12h2m4 0h10M4 18h8m4 0h4"/>',
  "ti-trash": '<path d="M4 7h16M10 11v6m4-6v6M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3"/>',
  "ti-pencil": '<path d="M4 20h4l10.5-10.5a2.828 2.828 0 1 0-4-4L4 16v4zm10.5-14.5 4 4"/>',
  "ti-info-circle": '<circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v4h1"/>',
  "ti-eye": '<circle cx="12" cy="12" r="2"/><path d="M22 12C19.333 6.667 16 4 12 4S4.667 6.667 2 12c2.667 5.333 6 8 10 8s7.333-2.667 10-8z"/>',
  "ti-eye-off": '<path d="M10.585 10.587a2 2 0 0 0 2.829 2.828M16.681 16.68A9.006 9.006 0 0 1 12 18c-4 0-7.333-2.667-10-8 1.394-2.788 2.944-4.815 4.654-6.073M9.168 9.165A9.05 9.05 0 0 0 2 12c2.667 5.333 6 8 10 8a9.053 9.053 0 0 0 5.834-2.165M6 6l12 12"/>',
  "ti-settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
};
const BRAND_ICONS = {
  "brand:discord": {
    color: "#5865F2",
    label: "Discord",
    svg: '<path fill="#5865F2" d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.002.022.015.043.03.056a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>'
  },
  "brand:spotify": {
    color: "#1DB954",
    label: "Spotify",
    svg: '<path fill="#1DB954" d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.36-.66.48-1.02.24-2.82-1.74-6.36-2.1-10.56-1.14-.42.12-.78-.18-.9-.54-.12-.42.18-.78.54-.9 4.56-1.02 8.52-.6 11.64 1.32.42.18.48.66.3 1.02zm1.44-3.3c-.3.42-.84.6-1.26.3-3.24-1.98-8.16-2.58-11.94-1.38-.48.12-1.02-.12-1.14-.6-.12-.48.12-1.02.6-1.14 4.38-1.32 9.84-.66 13.44 1.62.36.18.54.78.24 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.3c-.6.18-1.2-.18-1.38-.72-.18-.6.18-1.2.72-1.38 4.26-1.26 11.28-1.02 15.72 1.62.54.3.72 1.02.42 1.56-.3.42-1.02.6-1.56.3z"/>'
  },
  "brand:obs": {
    color: "#D0CEFF",
    label: "OBS Studio",
    src: "/assets/obs_icon.png"
  }
};
function getIconSvg(name) {
  return ICONS[name] ?? ICONS["ti-volume"];
}
function isBrandIcon(name) {
  return name.startsWith("brand:");
}
function getBrandIcon(name) {
  return BRAND_ICONS[name] ?? null;
}
function ChannelStrip($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let {
      channel,
      level = 0,
      status = "idle",
      onIconClick,
      onColorClick,
      onNameClick,
      onTypeClick,
      onDeviceClick,
      onToggle,
      onDelete,
      onVolumeChange,
      onContextMenu,
      onChannelPointerDown
    } = $$props;
    const DIR_COLORS = {
      OUT: "#22c55e",
      IN: "#3b82f6",
      APP: "#a855f7",
      MIC: "#f59e0b",
      MICOUT: "#ec4899"
    };
    const DIR_LABELS = {
      OUT: "OUT",
      IN: "IN",
      APP: "APP",
      MIC: "MIC IN",
      MICOUT: "MIC OUT"
    };
    const STATUS_DOT = {
      active: "#22c55e",
      error: "#ef4444",
      reconnecting: "#f59e0b",
      idle: "#444"
    };
    const accent = derived(() => channel.color || DIR_COLORS[channel.direction] || "#888");
    const dirCol = derived(() => DIR_COLORS[channel.direction] || "#888");
    const dirLbl = derived(() => DIR_LABELS[channel.direction] || "?");
    const icon = derived(() => getIconSvg(channel.icon));
    const brandIcon = derived(() => isBrandIcon(channel.icon) ? getBrandIcon(channel.icon) : null);
    const isManifestIcon = derived(() => !!channel.icon && !channel.icon.startsWith("ti-") && !channel.icon.startsWith("brand:") && !channel.icon.startsWith("data:") && !channel.icon.startsWith("http"));
    const dotCol = derived(() => STATUS_DOT[status] ?? "#444");
    const isOn = derived(() => channel.enabled);
    $$renderer2.push(`<div class="strip channel-strip svelte-veh2do"${attr("id", `s${stringify(channel.id)}`)}${attr("data-channel-id", channel.id)}${attr_style(`--accent:${stringify(accent())};--dir:${stringify(dirCol())};background:${stringify(accent())}18`)}><div class="accent-bar svelte-veh2do"></div> <button class="icon-wrap svelte-veh2do" style="background:rgba(0,0,0,0.12);border:1px solid rgba(255,255,255,0.06)" title="Change icon">`);
    if (channel.icon && (channel.icon.startsWith("data:") || channel.icon.startsWith("http") || channel.icon.startsWith("blob:"))) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<img${attr("src", channel.icon)} width="26" height="26" style="border-radius:4px;object-fit:contain" alt=""/>`);
    } else if (channel.custom_icon_base64) {
      $$renderer2.push("<!--[1-->");
      $$renderer2.push(`<img${attr("src", channel.custom_icon_base64)} width="26" height="26" style="border-radius:4px;object-fit:contain" alt=""/>`);
    } else if (isManifestIcon()) {
      $$renderer2.push("<!--[2-->");
      $$renderer2.push(`<img${attr("src", `/icons/${stringify(channel.icon)}.png`)} width="26" height="26" style="object-fit:contain" alt=""/>`);
    } else if (brandIcon()) {
      $$renderer2.push("<!--[3-->");
      if (brandIcon().src) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<img${attr("src", brandIcon().src)} width="26" height="26" style="object-fit:contain" alt=""/>`);
      } else {
        $$renderer2.push("<!--[-1-->");
        $$renderer2.push(`<svg viewBox="0 0 24 24" width="26" height="26">${html(brandIcon().svg)}</svg>`);
      }
      $$renderer2.push(`<!--]-->`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="26" height="26">${html(icon())}</svg>`);
    }
    $$renderer2.push(`<!--]--> <span class="pencil svelte-veh2do">✎</span></button> <div class="name-row svelte-veh2do"><button class="color-dot svelte-veh2do"${attr_style(`background:${stringify(accent())}`)} title="Change color"></button> <button class="name svelte-veh2do" title="Click to rename">${escape_html(channel.name)}</button></div> <div class="dir-port-row svelte-veh2do"><button class="dir-badge svelte-veh2do"${attr_style(`color:${stringify(dirCol())};border-color:${stringify(dirCol())}45;background:${stringify(dirCol())}18`)} title="Change type">${escape_html(dirLbl())}</button> <span class="port-badge svelte-veh2do" title="UDP port">:${escape_html(channel.port)}</span></div> <div class="fader-meter svelte-veh2do"><div class="fader-wrap svelte-veh2do" data-no-drag="" style="touch-action:none"><div class="fader-track svelte-veh2do"><div class="fader-fill svelte-veh2do"${attr_style(`height:${stringify(channel.volume)}%;background:${stringify(accent())}`)}></div> <div class="fader-knob svelte-veh2do"${attr_style(`bottom:calc(${stringify(channel.volume)}% - 4px)`)}></div></div></div> `);
    LevelMeter($$renderer2, { level, color: accent() });
    $$renderer2.push(`<!----></div> <div class="strip-foot svelte-veh2do"><div class="vol-pct svelte-veh2do">${escape_html(channel.volume)}%</div> <div class="status-row svelte-veh2do"><span class="status-dot svelte-veh2do"${attr_style(`background:${stringify(dotCol())}`)}></span> <span class="status-text svelte-veh2do">${escape_html(status)}</span></div> <button${attr_class("toggle-btn svelte-veh2do", void 0, { "on": isOn() })}${attr_style(isOn() ? `background:${accent()}22;border-color:${accent()}88;color:${accent()}` : "")}>${escape_html(isOn() ? "ON" : "OFF")}</button> <div class="bottom-row svelte-veh2do"><button class="device-btn svelte-veh2do"${attr("title", channel.device || "No device — click to set")}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="13" height="13">`);
    if (channel.direction === "IN" || channel.direction === "MICOUT") {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`${html('<path d="M3 14a9 9 0 0 1 18 0"/><path d="M3 14v4a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2H3zm18 0v4a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2h4z"/>')}`);
    } else if (channel.direction === "MIC") {
      $$renderer2.push("<!--[1-->");
      $$renderer2.push(`${html('<rect x="9" y="2" width="6" height="11" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 19v3M9 22h6"/>')}`);
    } else if (channel.direction === "APP") {
      $$renderer2.push("<!--[2-->");
      $$renderer2.push(`${html('<rect x="3" y="4" width="18" height="12" rx="1"/><path d="M1 20h22"/>')}`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`${html('<path d="M15 8a5 5 0 0 1 0 8"/><path d="M11 5 6 9H3v6h3l5 4V5z"/>')}`);
    }
    $$renderer2.push(`<!--]--></svg> `);
    if (!channel.device) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<svg class="no-device-slash svelte-veh2do" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" width="14" height="14"><path d="M5 19L19 5"></path></svg>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></button> <button class="del-btn svelte-veh2do" title="Remove channel">✕</button></div></div></div>`);
  });
}
function ContextMenu($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { x, y, channelEnabled } = $$props;
    $$renderer2.push(`<div class="backdrop svelte-jroghn"><div class="menu svelte-jroghn"${attr_style(`left:${stringify(x)}px;top:${stringify(y)}px`)}><button class="item svelte-jroghn">Rename Channel</button> <button class="item svelte-jroghn">Select Source</button> <button class="item svelte-jroghn">Change Direction</button> <button class="item svelte-jroghn">Change Color</button> <button class="item svelte-jroghn">Change Icon</button> <div class="sep svelte-jroghn"></div> <button class="item svelte-jroghn">${escape_html(channelEnabled ? "Turn Off" : "Turn On")}</button> <button class="item svelte-jroghn">Channel Info</button> <div class="sep svelte-jroghn"></div> <button class="item danger svelte-jroghn">Delete Channel</button></div></div>`);
  });
}
function IconPicker($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { currentIcon = "" } = $$props;
    let manifest = { brand: [], audio: [] };
    let urlInput = "";
    $$renderer2.push(`<div class="overlay svelte-on0603"><div class="modal svelte-on0603"><div class="modal-head svelte-on0603"><span class="modal-title svelte-on0603">Choose Icon</span> <button class="x-btn svelte-on0603">✕</button></div> <div class="scroll-area svelte-on0603">`);
    if (manifest.brand.length > 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="section-label svelte-on0603">Official App Icons</div> <div class="brand-grid svelte-on0603"><!--[-->`);
      const each_array = ensure_array_like(manifest.brand);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let icon = each_array[$$index];
        $$renderer2.push(`<button${attr_class("icon-cell brand-cell svelte-on0603", void 0, { "active": icon.id === currentIcon })}${attr_style(`background:${stringify(icon.id === currentIcon ? icon.color + "22" : "#0d1117")};border-color:${stringify(icon.id === currentIcon ? icon.color + "88" : "#21262d")}`)}${attr("title", icon.label)}><div class="brand-img-wrap svelte-on0603"${attr_style(`background:${stringify(icon.color)}18;border:1px solid ${stringify(icon.color)}33`)}><img${attr("src", icon.src)}${attr("alt", icon.label)} width="28" height="28" style="object-fit:contain"/></div> <span class="brand-name svelte-on0603"${attr_style(`color:${stringify(icon.color)}`)}>${escape_html(icon.label)}</span></button>`);
      }
      $$renderer2.push(`<!--]--></div> <div class="divider svelte-on0603"></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (manifest.audio.length > 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="section-label svelte-on0603">Audio &amp; Streaming</div> <div class="audio-grid svelte-on0603"><!--[-->`);
      const each_array_1 = ensure_array_like(manifest.audio);
      for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
        let icon = each_array_1[$$index_1];
        $$renderer2.push(`<button${attr_class("icon-cell audio-cell svelte-on0603", void 0, { "active": icon.id === currentIcon })}${attr_style(`background:${stringify(icon.id === currentIcon ? icon.color + "22" : "transparent")};border-color:${stringify(icon.id === currentIcon ? icon.color + "88" : "#21262d")}`)}${attr("title", icon.label)}><div class="audio-img-wrap svelte-on0603"${attr_style(`background:${stringify(icon.color)}18;border:1px solid ${stringify(icon.color)}33`)}><img${attr("src", icon.src)}${attr("alt", icon.label)} width="24" height="24" style="object-fit:contain"/></div> <span class="audio-label svelte-on0603"${attr_style(`color:${stringify(icon.color)}`)}>${escape_html(icon.label)}</span></button>`);
      }
      $$renderer2.push(`<!--]--></div> <div class="divider svelte-on0603"></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <div class="section-label svelte-on0603">Custom Image</div> <div class="url-row svelte-on0603"><input class="url-input svelte-on0603" type="text" placeholder="Paste image URL…"${attr("value", urlInput)}/> <button class="url-btn svelte-on0603">Use</button></div> <div class="file-row svelte-on0603"><input type="file" accept="image/*" style="display:none"/> <button class="browse-btn svelte-on0603">Browse local image…</button></div></div></div></div>`);
  });
}
function ColorPicker($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { currentColor = "#888888" } = $$props;
    const SWATCHES = [
      "#ff6b6b",
      "#ff9f43",
      "#ffd32a",
      "#05c46b",
      "#1db954",
      "#22c55e",
      "#3b82f6",
      "#5865f2",
      "#a855f7",
      "#ec4899",
      "#f59e0b",
      "#14b8a6",
      "#ef4444",
      "#8b5cf6",
      "#06b6d4",
      "#94a3b8"
    ];
    let pick = currentColor;
    $$renderer2.push(`<div class="overlay svelte-crjufj"><div class="modal svelte-crjufj"><div class="modal-head svelte-crjufj"><span class="modal-title svelte-crjufj">Choose Color</span> <button class="x-btn svelte-crjufj">✕</button></div> <div class="body svelte-crjufj"><div class="swatch-grid svelte-crjufj"><!--[-->`);
    const each_array = ensure_array_like(SWATCHES);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let s = each_array[$$index];
      $$renderer2.push(`<button class="swatch svelte-crjufj"${attr_style(`background:${stringify(s)};${stringify(pick === s ? "box-shadow:0 0 0 2px #e6edf3,0 0 0 4px " + s : "")}`)}></button>`);
    }
    $$renderer2.push(`<!--]--></div> <div class="custom-row svelte-crjufj"><span class="label svelte-crjufj">Custom</span> <input type="color"${attr("value", pick)} class="color-input svelte-crjufj"/> <span class="hex svelte-crjufj">${escape_html(pick)}</span></div> <div class="preview svelte-crjufj"${attr_style(`background:${stringify(pick)}22;border-color:${stringify(pick)}55`)}><span${attr_style(`color:${stringify(pick)};font-weight:700`)}>Preview</span></div></div> <div class="footer svelte-crjufj"><button class="cancel-btn svelte-crjufj">Cancel</button> <button class="ok-btn svelte-crjufj"${attr_style(`background:${stringify(pick)}`)}>Apply</button></div></div></div>`);
  });
}
function NameEditor($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { currentName = "" } = $$props;
    let value = currentName;
    $$renderer2.push(`<div class="overlay svelte-19sofos"><div class="modal svelte-19sofos"><div class="modal-head svelte-19sofos"><span class="modal-title svelte-19sofos">Rename Channel</span> <button class="x-btn svelte-19sofos">✕</button></div> <div class="body svelte-19sofos"><input class="name-input svelte-19sofos" type="text"${attr("value", value)} maxlength="16" placeholder="Channel name…" autofocus=""/> <div${attr_class("char-count svelte-19sofos", void 0, { "warn": value.length >= 14 })}>${escape_html(value.length)}/16</div></div> <div class="footer svelte-19sofos"><button class="cancel-btn svelte-19sofos">Cancel</button> <button class="save-btn svelte-19sofos">Save</button></div></div></div>`);
  });
}
function TypePicker($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { currentType = "OUT" } = $$props;
    const TYPES = [
      {
        id: "OUT",
        label: "Loopback Out",
        sub: "System audio → peer",
        color: "#22c55e",
        icon: "🔊"
      },
      {
        id: "IN",
        label: "Audio In",
        sub: "Receive audio → speaker",
        color: "#3b82f6",
        icon: "🎧"
      },
      {
        id: "APP",
        label: "App Capture",
        sub: "App process → peer",
        color: "#a855f7",
        icon: "🖥"
      },
      {
        id: "MIC",
        label: "MIC IN",
        sub: "Receive mic → output",
        color: "#f59e0b",
        icon: "🎤"
      },
      {
        id: "MICOUT",
        label: "MIC OUT",
        sub: "Mic capture → peer",
        color: "#ec4899",
        icon: "🎙"
      }
    ];
    $$renderer2.push(`<div class="overlay svelte-bpogfc"><div class="modal svelte-bpogfc"><div class="modal-head svelte-bpogfc"><span class="modal-title svelte-bpogfc">Channel Type</span> <button class="x-btn svelte-bpogfc">✕</button></div> <div class="grid svelte-bpogfc"><!--[-->`);
    const each_array = ensure_array_like(TYPES);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let t = each_array[$$index];
      $$renderer2.push(`<button${attr_class("type-cell svelte-bpogfc", void 0, { "active": t.id === currentType })}${attr_style(t.id === currentType ? `border-color:${t.color};background:${t.color}18` : "")}><span class="type-icon svelte-bpogfc">${escape_html(t.icon)}</span> <span class="type-label svelte-bpogfc"${attr_style(t.id === currentType ? `color:${t.color}` : "")}>${escape_html(t.label)}</span> <span class="type-sub svelte-bpogfc">${escape_html(t.sub)}</span></button>`);
    }
    $$renderer2.push(`<!--]--></div></div></div>`);
  });
}
function DevicePicker($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { direction = "OUT" } = $$props;
    let loading = true;
    const labelMap = {
      OUT: "Loopback Devices",
      IN: "Output Devices",
      MIC: "Output Devices",
      MICOUT: "Input Devices",
      APP: "App Audio Sources"
    };
    $$renderer2.push(`<div class="overlay svelte-1md6d9m"><div class="modal svelte-1md6d9m"><div class="modal-head svelte-1md6d9m"><span class="modal-title svelte-1md6d9m">${escape_html(labelMap[direction] ?? "Devices")}</span> <div class="head-btns svelte-1md6d9m"><button class="refresh-btn svelte-1md6d9m" title="Refresh list"${attr("disabled", loading, true)}>↻</button> <button class="x-btn svelte-1md6d9m">✕</button></div></div> <div class="list-wrap svelte-1md6d9m">`);
    {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="placeholder svelte-1md6d9m">Loading…</div>`);
    }
    $$renderer2.push(`<!--]--></div></div></div>`);
  });
}
function ChannelInfo($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { channel, status = "idle" } = $$props;
    const DIR_LABELS = {
      OUT: "Loopback Out",
      IN: "Audio In",
      APP: "App Capture",
      MIC: "Mic In",
      MICOUT: "Mic Out"
    };
    const DIR_COLORS = {
      OUT: "#22c55e",
      IN: "#3b82f6",
      APP: "#a855f7",
      MIC: "#f59e0b",
      MICOUT: "#ec4899"
    };
    const dirLabel = derived(() => DIR_LABELS[channel.direction] ?? channel.direction);
    const dirColor = derived(() => DIR_COLORS[channel.direction] ?? "#888");
    let portValue = String(channel.port);
    $$renderer2.push(`<div class="overlay svelte-1ymujip"><div class="modal svelte-1ymujip"><div class="modal-head svelte-1ymujip"><span class="modal-title svelte-1ymujip">Channel Info</span> <button class="x-btn svelte-1ymujip">✕</button></div> <div class="body svelte-1ymujip"><div class="row svelte-1ymujip"><span class="lbl svelte-1ymujip">Name</span> <span class="val svelte-1ymujip">${escape_html(channel.name)}</span></div> <div class="row svelte-1ymujip"><span class="lbl svelte-1ymujip">Direction</span> <span class="val svelte-1ymujip"${attr_style(`color:${stringify(dirColor())}`)}>${escape_html(dirLabel())}</span></div> <div class="row svelte-1ymujip"><span class="lbl svelte-1ymujip">Device</span> <span class="val mono svelte-1ymujip">${escape_html(channel.device || "—")}</span></div> <div class="row port-row svelte-1ymujip"><span class="lbl svelte-1ymujip">Port</span> <div class="port-edit svelte-1ymujip"><input${attr_class("port-input svelte-1ymujip", void 0, { "err": false })} type="number" min="1024" max="65535"${attr("value", portValue)}/> <button class="port-apply svelte-1ymujip" title="Apply port">✔</button></div></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <div class="row svelte-1ymujip"><span class="lbl svelte-1ymujip">Volume</span> <span class="val svelte-1ymujip">${escape_html(channel.volume)}%</span></div> <div class="row svelte-1ymujip"><span class="lbl svelte-1ymujip">Status</span> <span class="val svelte-1ymujip">${escape_html(channel.enabled ? status : "disabled")}</span></div> <div class="row svelte-1ymujip"><span class="lbl svelte-1ymujip">ID</span> <span class="val mono small svelte-1ymujip">${escape_html(channel.id)}</span></div> <div class="color-preview svelte-1ymujip"${attr_style(`background:${stringify(channel.color)}22;border-color:${stringify(channel.color)}55`)}><span${attr_style(`color:${stringify(channel.color)};font-weight:700;font-size:11px`)}>${escape_html(channel.color)}</span></div></div> <div class="footer svelte-1ymujip"><button class="close-btn svelte-1ymujip">Close</button></div></div></div>`);
  });
}
let config = {
  gaming_channels: []
};
let engineRunning = { value: false };
let peerStatus = { connected: false };
let channelLevels = {};
async function setChannelVolume(channelId, volume) {
  await invoke("set_channel_volume", { channelId, volume });
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const channels = derived(() => config.gaming_channels);
    const outgoing = derived(() => channels().filter((ch) => ch.direction === "OUT" || ch.direction === "APP"));
    const incoming = derived(() => channels().filter((ch) => ch.direction === "IN"));
    const micInputs = derived(() => channels().filter((ch) => ch.direction === "MIC"));
    const micOut = derived(() => channels().filter((ch) => ch.direction === "MICOUT"));
    function onPointerDown(e, channelId, section) {
      if (
        /** @type {HTMLElement} */
        e.target.closest("[data-no-drag], button, input, select")
      ) return;
      e.preventDefault();
      ({
        channelId,
        section,
        startX: e.clientX,
        dragging: false,
        clone: null,
        rect: null,
        insertBefore: null
      });
    }
    let activeModal = null;
    function openModal(type, channelId) {
      activeModal = { type, channelId };
    }
    function findChannel(id) {
      return config.gaming_channels.find((c) => c.id === id);
    }
    function updateChannel(id, patch) {
      const ch = findChannel(id);
      if (ch) Object.assign(ch, patch);
    }
    async function hotswapChannel(id) {
      return;
    }
    let pendingDelete = null;
    function removeChannel(id) {
      pendingDelete = id;
    }
    function toggleChannel(id) {
      const ch = findChannel(id);
      if (ch) {
        ch.enabled = !ch.enabled;
        hotswapChannel();
      }
    }
    let contextMenu = null;
    function openContextMenu(e, channelId) {
      const x = Math.min(e.clientX, window.innerWidth - 190);
      const y = Math.min(e.clientY, window.innerHeight - 260);
      contextMenu = { channelId, x, y };
    }
    let showSettings = false;
    let showLog = false;
    function chStatus(id) {
      return "idle";
    }
    $$renderer2.push(`<header class="topbar svelte-1uha8ag"><div class="brand svelte-1uha8ag"><img src="/assets/shadowbridge_icon_64.png" width="32" height="32" style="object-fit: contain;" alt="" class="svelte-1uha8ag"/> <img src="/assets/shadowbridge_wordmark.png" height="22" style="object-fit: contain; width: auto;" alt="ShadowBridge" class="svelte-1uha8ag"/></div> <div class="topbar-btns svelte-1uha8ag"><button class="tb-btn mode-btn svelte-1uha8ag"><span class="mode-dot svelte-1uha8ag"></span> ${escape_html("Gaming PC")}</button> <button${attr_class("tb-btn svelte-1uha8ag", void 0, { "tb-active": showLog })}>Log</button> <button${attr_class("tb-btn svelte-1uha8ag", void 0, { "tb-active": showSettings })}>Settings</button></div></header> <div class="statusbar svelte-1uha8ag"><span${attr_class("peer-dot svelte-1uha8ag", void 0, { "connected": peerStatus.connected })}></span> <span class="peer-text svelte-1uha8ag">`);
    {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`Searching for peer on ${escape_html("●●●.●●●.●.●●●")}`);
    }
    $$renderer2.push(`<!--]--></span> <button class="eye-btn svelte-1uha8ag" title="Toggle IP visibility">${escape_html("👁")}</button> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <main class="main svelte-1uha8ag"><div class="strips-row svelte-1uha8ag"><div class="section-div svelte-1uha8ag"><div class="div-line svelte-1uha8ag"></div> <span class="div-label svelte-1uha8ag" style="color:#22c55e">OUTGOING</span> <div class="div-line svelte-1uha8ag"></div> <button class="add-btn svelte-1uha8ag" style="color:#22c55e;border-color:#22c55e66" title="Add output channel">+</button></div> <div data-section="out" style="display:contents" class="svelte-1uha8ag"><!--[-->`);
    const each_array_1 = ensure_array_like(outgoing());
    for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
      let ch = each_array_1[$$index_1];
      ChannelStrip($$renderer2, {
        channel: ch,
        level: channelLevels[ch.id] ?? 0,
        status: chStatus(ch.id),
        onIconClick: () => openModal("icon", ch.id),
        onColorClick: () => openModal("color", ch.id),
        onNameClick: () => openModal("name", ch.id),
        onTypeClick: () => openModal("type", ch.id),
        onDeviceClick: () => openModal("device", ch.id),
        onToggle: () => toggleChannel(ch.id),
        onDelete: () => removeChannel(ch.id),
        onVolumeChange: (v) => {
          updateChannel(ch.id, { volume: v });
          setChannelVolume(ch.id, v);
        },
        onContextMenu: (e) => openContextMenu(e, ch.id),
        onChannelPointerDown: (e) => onPointerDown(e, ch.id, "out")
      });
    }
    $$renderer2.push(`<!--]--></div> <div class="section-div svelte-1uha8ag"><div class="div-line svelte-1uha8ag"></div> <span class="div-label svelte-1uha8ag" style="color:#3b82f6">INCOMING</span> <div class="div-line svelte-1uha8ag"></div> <button class="add-btn svelte-1uha8ag" style="color:#3b82f6;border-color:#3b82f666" title="Add input channel">+</button></div> <div data-section="in" style="display:contents" class="svelte-1uha8ag"><!--[-->`);
    const each_array_2 = ensure_array_like(incoming());
    for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
      let ch = each_array_2[$$index_2];
      ChannelStrip($$renderer2, {
        channel: ch,
        level: channelLevels[ch.id] ?? 0,
        status: chStatus(ch.id),
        onIconClick: () => openModal("icon", ch.id),
        onColorClick: () => openModal("color", ch.id),
        onNameClick: () => openModal("name", ch.id),
        onTypeClick: () => openModal("type", ch.id),
        onDeviceClick: () => openModal("device", ch.id),
        onToggle: () => toggleChannel(ch.id),
        onDelete: () => removeChannel(ch.id),
        onVolumeChange: (v) => {
          updateChannel(ch.id, { volume: v });
          setChannelVolume(ch.id, v);
        },
        onContextMenu: (e) => openContextMenu(e, ch.id),
        onChannelPointerDown: (e) => onPointerDown(e, ch.id, "in")
      });
    }
    $$renderer2.push(`<!--]--></div> <div class="section-div svelte-1uha8ag"><div class="div-line svelte-1uha8ag"></div> <span class="div-label svelte-1uha8ag" style="color:#f59e0b">MIC INPUTS</span> <div class="div-line svelte-1uha8ag"></div> <button class="add-btn svelte-1uha8ag" style="color:#f59e0b;border-color:#f59e0b66" title="Add mic input channel">+</button></div> <div data-section="mic" style="display:contents" class="svelte-1uha8ag"><!--[-->`);
    const each_array_3 = ensure_array_like(micInputs());
    for (let $$index_3 = 0, $$length = each_array_3.length; $$index_3 < $$length; $$index_3++) {
      let ch = each_array_3[$$index_3];
      ChannelStrip($$renderer2, {
        channel: ch,
        level: channelLevels[ch.id] ?? 0,
        status: chStatus(ch.id),
        onIconClick: () => openModal("icon", ch.id),
        onColorClick: () => openModal("color", ch.id),
        onNameClick: () => openModal("name", ch.id),
        onTypeClick: () => openModal("type", ch.id),
        onDeviceClick: () => openModal("device", ch.id),
        onToggle: () => toggleChannel(ch.id),
        onDelete: () => removeChannel(ch.id),
        onVolumeChange: (v) => {
          updateChannel(ch.id, { volume: v });
          setChannelVolume(ch.id, v);
        },
        onContextMenu: (e) => openContextMenu(e, ch.id),
        onChannelPointerDown: (e) => onPointerDown(e, ch.id, "mic")
      });
    }
    $$renderer2.push(`<!--]--></div> <div class="section-div svelte-1uha8ag"><div class="div-line svelte-1uha8ag"></div> <span class="div-label svelte-1uha8ag" style="color:#e879f9">MIC OUTPUTS</span> <div class="div-line svelte-1uha8ag"></div> <button class="add-btn svelte-1uha8ag" style="color:#e879f9;border-color:#e879f966" title="Add mic output channel">+</button></div> <div data-section="micout" style="display:contents" class="svelte-1uha8ag"><!--[-->`);
    const each_array_4 = ensure_array_like(micOut());
    for (let $$index_4 = 0, $$length = each_array_4.length; $$index_4 < $$length; $$index_4++) {
      let ch = each_array_4[$$index_4];
      ChannelStrip($$renderer2, {
        channel: ch,
        level: channelLevels[ch.id] ?? 0,
        status: chStatus(ch.id),
        onIconClick: () => openModal("icon", ch.id),
        onColorClick: () => openModal("color", ch.id),
        onNameClick: () => openModal("name", ch.id),
        onTypeClick: () => openModal("type", ch.id),
        onDeviceClick: () => openModal("device", ch.id),
        onToggle: () => toggleChannel(ch.id),
        onDelete: () => removeChannel(ch.id),
        onVolumeChange: (v) => {
          updateChannel(ch.id, { volume: v });
          setChannelVolume(ch.id, v);
        },
        onContextMenu: (e) => openContextMenu(e, ch.id),
        onChannelPointerDown: (e) => onPointerDown(e, ch.id, "micout")
      });
    }
    $$renderer2.push(`<!--]--></div></div></main> <footer class="bottom-bar svelte-1uha8ag"><button class="start-btn svelte-1uha8ag"${attr("disabled", engineRunning.value, true)}>▶ Start All</button> <button class="stop-btn svelte-1uha8ag"${attr("disabled", true, true)}>■ Stop All</button></footer> <div class="sysbar svelte-1uha8ag"><span class="svelte-1uha8ag">v0.4.0</span> <span class="sys-status svelte-1uha8ag">SYS: ${escape_html("NOMINAL")}</span></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (contextMenu) {
      $$renderer2.push("<!--[0-->");
      const _ch = findChannel(contextMenu.channelId);
      ContextMenu($$renderer2, {
        x: contextMenu.x,
        y: contextMenu.y,
        channelEnabled: _ch?.enabled ?? true
      });
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (activeModal?.type === "icon") {
      $$renderer2.push("<!--[0-->");
      const ch = findChannel(activeModal.channelId);
      if (ch) {
        $$renderer2.push("<!--[0-->");
        IconPicker($$renderer2, {
          color: ch.color,
          currentIcon: ch.icon
        });
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]-->`);
    } else if (activeModal?.type === "color") {
      $$renderer2.push("<!--[1-->");
      const ch = findChannel(activeModal.channelId);
      if (ch) {
        $$renderer2.push("<!--[0-->");
        ColorPicker($$renderer2, {
          currentColor: ch.color
        });
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]-->`);
    } else if (activeModal?.type === "name") {
      $$renderer2.push("<!--[2-->");
      const ch = findChannel(activeModal.channelId);
      if (ch) {
        $$renderer2.push("<!--[0-->");
        NameEditor($$renderer2, {
          currentName: ch.name
        });
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]-->`);
    } else if (activeModal?.type === "type") {
      $$renderer2.push("<!--[3-->");
      const ch = findChannel(activeModal.channelId);
      if (ch) {
        $$renderer2.push("<!--[0-->");
        TypePicker($$renderer2, {
          currentType: ch.direction
        });
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]-->`);
    } else if (activeModal?.type === "device") {
      $$renderer2.push("<!--[4-->");
      const ch = findChannel(activeModal.channelId);
      if (ch) {
        $$renderer2.push("<!--[0-->");
        DevicePicker($$renderer2, {
          direction: ch.direction,
          currentDevice: ch.device
        });
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]-->`);
    } else if (activeModal?.type === "info") {
      $$renderer2.push("<!--[5-->");
      const ch = findChannel(activeModal.channelId);
      if (ch) {
        $$renderer2.push("<!--[0-->");
        ChannelInfo($$renderer2, {
          channel: ch,
          status: chStatus(ch.id)
        });
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]-->`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (pendingDelete) {
      $$renderer2.push("<!--[0-->");
      const ch = findChannel(pendingDelete);
      $$renderer2.push(`<div class="confirm-backdrop svelte-1uha8ag" role="dialog" aria-modal="true"><div class="confirm-box svelte-1uha8ag"><p class="confirm-msg svelte-1uha8ag">Delete <strong class="svelte-1uha8ag">${escape_html(ch?.name ?? "this channel")}</strong>?</p> <p class="confirm-sub svelte-1uha8ag">This cannot be undone.</p> <div class="confirm-btns svelte-1uha8ag"><button class="confirm-cancel svelte-1uha8ag">Cancel</button> <button class="confirm-ok svelte-1uha8ag">Delete</button></div></div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]-->`);
  });
}
export {
  _page as default
};
