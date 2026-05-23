<script>
  import LevelMeter from './LevelMeter.svelte';
  import { getIconSvg, isBrandIcon, getBrandIcon } from './icons.js';

  function hexAlpha(hex, opacity) {
    const c = hex.replace('#','').padEnd(6,'0');
    const r = parseInt(c.slice(0,2),16), g = parseInt(c.slice(2,4),16), b = parseInt(c.slice(4,6),16);
    return `rgba(${r},${g},${b},${opacity})`;
  }

  /**
   * @type {{
   *   channel: import('./store.svelte.js').ChannelConfig,
   *   level?: number,
   *   status?: string,
   *   onIconClick?: () => void,
   *   onColorClick?: () => void,
   *   onNameClick?: () => void,
   *   onTypeClick?: () => void,
   *   onDeviceClick?: () => void,
   *   onToggle?: () => void,
   *   onDelete?: () => void,
   *   onVolumeChange?: (v: number) => void,
   *   onContextMenu?: (e: MouseEvent) => void,
   * }}
   */
  let {
    channel,
    level = 0,
    status = 'idle',
    onIconClick,
    onColorClick,
    onNameClick,
    onTypeClick,
    onDeviceClick,
    onToggle,
    onDelete,
    onVolumeChange,
    onContextMenu,
    onChannelPointerDown,
  } = $props();

  const DIR_COLORS = { OUT: '#22c55e', IN: '#3b82f6', APP: '#a855f7', MIC: '#f59e0b', MICOUT: '#ec4899' };
  const DIR_LABELS = { OUT: 'OUT', IN: 'IN', APP: 'APP', MIC: 'MIC IN', MICOUT: 'MIC OUT' };
  const STATUS_DOT = {
    active:       '#22c55e',
    error:        '#ef4444',
    reconnecting: '#f59e0b',
    idle:         '#444',
  };

  const accent    = $derived(channel.color || DIR_COLORS[channel.direction] || '#888');
  const dirCol    = $derived(DIR_COLORS[channel.direction] || '#888');
  const dirLbl    = $derived(DIR_LABELS[channel.direction] || '?');
  const icon      = $derived(getIconSvg(channel.icon));
  const brandIcon = $derived(isBrandIcon(channel.icon) ? getBrandIcon(channel.icon) : null);
  // True when icon is a manifest PNG (not a ti- class, brand:, data URL, or http URL)
  const isManifestIcon = $derived(
    !!channel.icon &&
    !channel.icon.startsWith('ti-') &&
    !channel.icon.startsWith('brand:') &&
    !channel.icon.startsWith('data:') &&
    !channel.icon.startsWith('http')
  );
  const dotCol    = $derived(STATUS_DOT[status] ?? '#444');
  const isOn      = $derived(channel.enabled);

  /** @type {HTMLDivElement | null} */
  let trackWrapEl = $state(null);

  /** @param {PointerEvent} e */
  function faderPointerDown(e) {
    /** @type {HTMLElement} */ (e.currentTarget).setPointerCapture(e.pointerId);
    updateFader(e);
  }

  /** @param {PointerEvent} e */
  function faderPointerMove(e) {
    if (e.buttons === 0) return;
    updateFader(e);
  }

  /** @param {PointerEvent} e */
  function updateFader(e) {
    if (!trackWrapEl) return;
    const rect = trackWrapEl.getBoundingClientRect();
    const ratio = 1 - (e.clientY - rect.top) / rect.height;
    const vol = Math.round(Math.max(0, Math.min(1, ratio)) * 100);
    onVolumeChange?.(vol);
  }
</script>

<div class="strip channel-strip"
  id="s{channel.id}"
  data-channel-id={channel.id}
  style="--accent:{accent};--dir:{dirCol};background:{accent}18"
  onpointerdown={onChannelPointerDown}
  oncontextmenu={e => { e.preventDefault(); onContextMenu?.(e); }}>

  <!-- accent bar -->
  <div class="accent-bar"></div>

  <!-- icon -->
  <button class="icon-wrap" style="background:rgba(0,0,0,0.12);border:1px solid rgba(255,255,255,0.06)" onclick={onIconClick} title="Change icon">
    {#if channel.icon && (channel.icon.startsWith('data:') || channel.icon.startsWith('http') || channel.icon.startsWith('blob:'))}
      <img src={channel.icon} width="26" height="26" style="border-radius:4px;object-fit:contain" alt="" />
    {:else if channel.custom_icon_base64}
      <img src={channel.custom_icon_base64} width="26" height="26" style="border-radius:4px;object-fit:contain" alt="" />
    {:else if isManifestIcon}
      <img src="/icons/{channel.icon}.png" width="26" height="26" style="object-fit:contain" alt="" />
    {:else if brandIcon}
      {#if brandIcon.src}
        <img src={brandIcon.src} width="26" height="26" style="object-fit:contain" alt="" />
      {:else}
        <svg viewBox="0 0 24 24" width="26" height="26">
          {@html brandIcon.svg}
        </svg>
      {/if}
    {:else}
      <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round" width="26" height="26">
        {@html icon}
      </svg>
    {/if}
    <span class="pencil">✎</span>
  </button>

  <!-- name row -->
  <div class="name-row">
    <button class="color-dot" style="background:{accent}" onclick={onColorClick} title="Change color"></button>
    <button class="name" onclick={onNameClick} title="Click to rename">{channel.name}</button>
  </div>

  <!-- direction badge + port -->
  <div class="dir-port-row">
    <button
      class="dir-badge"
      style="color:{dirCol};border-color:{dirCol}45;background:{dirCol}18"
      onclick={onTypeClick}
      title="Change type"
    >
      {dirLbl}
    </button>
    <span class="port-badge" title="UDP port">:{channel.port}</span>
  </div>

  <!-- fader + meter -->
  <div class="fader-meter">
    <div class="fader-wrap" bind:this={trackWrapEl}
      data-no-drag
      onpointerdown={faderPointerDown}
      onpointermove={faderPointerMove}
      style="touch-action:none"
    >
      <div class="fader-track">
        <div class="fader-fill" style="height:{channel.volume}%;background:{accent}"></div>
        <div class="fader-knob" style="bottom:calc({channel.volume}% - 4px)"></div>
      </div>
    </div>
    <LevelMeter {level} color={accent} />
  </div>

  <!-- bottom controls — margin-top:auto keeps these anchored to the strip bottom -->
  <div class="strip-foot">
    <div class="vol-pct">{channel.volume}%</div>

    <div class="status-row">
      <span class="status-dot" style="background:{dotCol}"></span>
      <span class="status-text">{status}</span>
    </div>

    <button
      class="toggle-btn"
      class:on={isOn}
      onclick={onToggle}
      style={isOn ? `background:${accent}22;border-color:${accent}88;color:${accent}` : ''}
    >
      {isOn ? 'ON' : 'OFF'}
    </button>

    <div class="bottom-row">
      <button class="device-btn" onclick={onDeviceClick} title={channel.device || 'No device — click to set'}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" width="13" height="13">
          {#if channel.direction === 'IN' || channel.direction === 'MICOUT'}
            {@html '<path d="M3 14a9 9 0 0 1 18 0"/><path d="M3 14v4a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2H3zm18 0v4a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2h4z"/>'}
          {:else if channel.direction === 'MIC'}
            {@html '<rect x="9" y="2" width="6" height="11" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 19v3M9 22h6"/>'}
          {:else if channel.direction === 'APP'}
            {@html '<rect x="3" y="4" width="18" height="12" rx="1"/><path d="M1 20h22"/>'}
          {:else}
            {@html '<path d="M15 8a5 5 0 0 1 0 8"/><path d="M11 5 6 9H3v6h3l5 4V5z"/>'}
          {/if}
        </svg>
        {#if !channel.device}
          <svg class="no-device-slash" viewBox="0 0 24 24" fill="none"
               stroke="#ef4444" stroke-width="2.5" stroke-linecap="round"
               width="14" height="14">
            <path d="M5 19L19 5"/>
          </svg>
        {/if}
      </button>
      <button class="del-btn" onclick={onDelete} title="Remove channel">✕</button>
    </div>
  </div>
</div>

<style>
.strip {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 92px;
  border-radius: 8px;
  border: 1px solid #21262d;
  flex-shrink: 0;
  gap: 6px;
  position: relative;
  cursor: grab;
  user-select: none;
}

.accent-bar {
  width: 100%;
  height: 3px;
  background: var(--accent);
  border-radius: 7px 7px 0 0;
  flex-shrink: 0;
}

.icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: filter 0.15s;
  flex-shrink: 0;
}
.icon-wrap:hover { filter: brightness(1.2); }
.pencil {
  position: absolute;
  bottom: -4px;
  right: -4px;
  width: 16px;
  height: 16px;
  background: #21262d;
  border-radius: 50%;
  font-size: 9px;
  color: #8b949e;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 0 7px;
  min-width: 0;
}
.color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: transform 0.15s;
}
.color-dot:hover { transform: scale(1.3); }
.name {
  flex: 1;
  font-size: 11px;
  font-weight: 600;
  color: #e6edf3;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: normal;
  word-break: break-word;
  text-align: center;
  font-family: 'Figtree', sans-serif;
  line-height: 1.25;
  min-width: 0;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  border-radius: 3px;
  transition: color 0.15s;
}
.name:hover { color: #fff; }

.dir-port-row {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.dir-badge {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid;
  cursor: pointer;
  background: none;
  font-family: 'Figtree', sans-serif;
  transition: filter 0.15s;
  flex-shrink: 0;
}
.dir-badge:hover { filter: brightness(1.25); }

.port-badge {
  font-size: 9px;
  font-family: monospace;
  color: #555;
  flex-shrink: 0;
  letter-spacing: 0;
}

.fader-meter {
  display: flex;
  align-items: stretch;
  gap: 5px;
  width: 100%;
  flex: 1;
  min-height: 50px;
  padding: 2px 10px;
}

.fader-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  cursor: ns-resize;
  user-select: none;
}

.fader-track {
  width: 4px;
  height: 100%;
  background: #21262d;
  border-radius: 2px;
  position: relative;
}

.fader-fill {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 4px;
  border-radius: 2px;
}

.fader-knob {
  position: absolute;
  width: 22px;
  height: 7px;
  background: #adbac7;
  border-radius: 3px;
  left: -9px;
  pointer-events: none;
}

.strip-foot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  width: 100%;
  padding-bottom: 9px;
}

.vol-pct {
  font-size: 10px;
  color: #8b949e;
  font-family: 'Figtree', sans-serif;
  letter-spacing: 0.04em;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 4px;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-text {
  font-size: 9px;
  color: #8b949e;
  font-family: 'Figtree', sans-serif;
  text-transform: lowercase;
}

.toggle-btn {
  width: 62px;
  height: 26px;
  border-radius: 13px;
  border: 1px solid #333;
  background: #21262d;
  color: #555;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  cursor: pointer;
  font-family: 'Figtree', sans-serif;
  transition: all 0.15s;
  flex-shrink: 0;
}
.toggle-btn:hover { filter: brightness(1.2); }

.bottom-row {
  display: flex;
  gap: 4px;
  width: 100%;
  padding: 0 7px;
}
.device-btn {
  flex: 1;
  height: 24px;
  border-radius: 5px;
  border: 1px solid #21303e;
  background: #0f1e2a;
  color: #8b949e;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.15s;
  position: relative;
}
.device-btn:hover { border-color: var(--accent); color: var(--accent); }
.no-device-slash {
  position: absolute;
  pointer-events: none;
}
.del-btn {
  flex: 1;
  height: 24px;
  border-radius: 5px;
  border: 1px solid #3a1e1a;
  background: #1e1014;
  color: #ff6b6b;
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.del-btn:hover { background: #2d1018; border-color: #5a2a28; }
</style>
