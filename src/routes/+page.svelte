<script>
  import ChannelStrip  from '$lib/ChannelStrip.svelte';
  import ContextMenu   from '$lib/ContextMenu.svelte';
  import IconPicker    from '$lib/modals/IconPicker.svelte';
  import ColorPicker   from '$lib/modals/ColorPicker.svelte';
  import NameEditor    from '$lib/modals/NameEditor.svelte';
  import TypePicker    from '$lib/modals/TypePicker.svelte';
  import DevicePicker  from '$lib/modals/DevicePicker.svelte';
  import ChannelInfo   from '$lib/modals/ChannelInfo.svelte';

  import { invoke } from '@tauri-apps/api/core';
  import { getVersion } from '@tauri-apps/api/app';

  import { BRAND_ICONS } from '$lib/icons.js';
  import { listen } from '@tauri-apps/api/event';
  import {
    config, engineRunning, peerStatus,
    channelLevels, channelStatuses, engineError,
    loadConfig, saveConfig, startEngine, stopEngine, setupListeners,
    setChannelVolume, clearEngineError, startMonitoring, stopMonitoring,
    restartEngineChannel, sendPeerCommand,
  } from '$lib/store.svelte.js';

  let configLoaded = $state(false);
  let appVersion = $state('');
  $effect(() => { getVersion().then(v => { appVersion = 'v' + v; }); });
  let _saveTimer;
  let _monitorTimer;

  function scheduleSave() {
    clearTimeout(_saveTimer);
    _saveTimer = setTimeout(() => saveConfig().catch(() => {}), 400);
  }

  function scheduleMonitorRestart() {
    clearTimeout(_monitorTimer);
    _monitorTimer = setTimeout(() => startMonitoring().catch(() => {}), 300);
  }

  $effect(() => {
    JSON.stringify(config);
    if (configLoaded) {
      scheduleSave();
      scheduleMonitorRestart();
    }
  });

  // ── Derived sections ──────────────────────────────────────────────────────────
  const channels   = $derived(config.mode === 'gaming' ? config.gaming_channels : config.streaming_channels);
  const outgoing   = $derived(channels.filter(ch => ch.direction === 'OUT' || ch.direction === 'APP'));
  const incoming   = $derived(channels.filter(ch => ch.direction === 'IN'));
  const micInputs  = $derived(channels.filter(ch => ch.direction === 'MIC'));
  const micOut     = $derived(channels.filter(ch => ch.direction === 'MICOUT'));
  const destIp     = $derived(config.mode === 'gaming' ? config.streaming_ip : config.gaming_ip);

  function applyPeerIp() {
    if (!peerStatus.ip) return;
    if (config.mode === 'gaming') config.streaming_ip = peerStatus.ip;
    else config.gaming_ip = peerStatus.ip;
  }

  // Auto-fill when peer appears and the field is empty.
  $effect(() => {
    if (peerStatus.connected && peerStatus.ip && !destIp) applyPeerIp();
  });

  // Auto-start streams when peer detected and setting enabled.
  $effect(() => {
    if (peerStatus.connected && config.auto_start_streams && !engineRunning.value) {
      handleStart();
    }
  });

  // ── Drag-and-drop (pointer-based) ────────────────────────────────────────────
  /** @type {HTMLDivElement|null} */
  let stripsRowEl = null;

  /**
   * @type {{
   *   channelId: string, section: string,
   *   startX: number, dragging: boolean,
   *   clone: HTMLElement|null, rect: DOMRect|null,
   *   insertBefore: string|null
   * }|null}
   */
  let dragState = null;

  /** @param {PointerEvent} e @param {string} channelId @param {string} section */
  function onPointerDown(e, channelId, section) {
    if (/** @type {HTMLElement} */ (e.target).closest('[data-no-drag], button, input, select')) return;
    e.preventDefault();
    stripsRowEl?.setPointerCapture(e.pointerId);
    dragState = { channelId, section, startX: e.clientX, dragging: false, clone: null, rect: null, insertBefore: null };
  }

  /** @param {PointerEvent} e */
  function onPointerMove(e) {
    if (!dragState) return;

    if (!dragState.dragging && Math.abs(e.clientX - dragState.startX) < 6) return;

    if (!dragState.dragging) {
      dragState.dragging = true;
      const strip = document.getElementById('s' + dragState.channelId);
      if (!strip) return;
      const clone = /** @type {HTMLElement} */ (strip.cloneNode(true));
      clone.style.cssText = `position:fixed;opacity:0.6;pointer-events:none;z-index:1000;width:${strip.offsetWidth}px;transform:scale(1.04);transition:none;`;
      document.body.appendChild(clone);
      dragState.clone = clone;
      dragState.rect = strip.getBoundingClientRect();
    }

    const dx = e.clientX - dragState.startX;
    if (dragState.clone && dragState.rect) {
      dragState.clone.style.left = (dragState.rect.left + dx) + 'px';
      dragState.clone.style.top  = dragState.rect.top + 'px';
    }

    const strips = Array.from(document.querySelectorAll(`[data-section="${dragState.section}"] .channel-strip`));
    dragState.insertBefore = null;
    for (const s of strips) {
      const r = s.getBoundingClientRect();
      if (e.clientX < r.left + r.width / 2) {
        dragState.insertBefore = /** @type {HTMLElement} */ (s).dataset.channelId ?? null;
        break;
      }
    }

    strips.forEach(s => s.classList.remove('drag-insert-before'));
    if (dragState.insertBefore) {
      document.querySelector(`[data-channel-id="${dragState.insertBefore}"]`)?.classList.add('drag-insert-before');
    }
  }

  /** @param {PointerEvent} _e */
  function onPointerUp(_e) {
    if (!dragState) return;

    if (dragState.dragging) {
      dragState.clone?.remove();
      document.querySelectorAll('.drag-insert-before').forEach(el => el.classList.remove('drag-insert-before'));

      const { channelId, section, insertBefore } = dragState;
      if (insertBefore !== channelId) {
        const key = config.mode === 'gaming' ? 'gaming_channels' : 'streaming_channels';
        const arr = [...config[key]];
        const fromIdx = arr.findIndex(c => c.id === channelId);
        const [item] = arr.splice(fromIdx, 1);

        if (insertBefore) {
          const toIdx = arr.findIndex(c => c.id === insertBefore);
          if (toIdx !== -1) arr.splice(toIdx, 0, item);
          else arr.push(item);
        } else {
          // dropped past last strip — append after last channel of this section
          const sectionDirs = { out: ['OUT', 'APP'], in: ['IN'], mic: ['MIC'], micout: ['MICOUT'] };
          const dirs = sectionDirs[section] ?? [];
          let lastIdx = -1;
          for (let i = 0; i < arr.length; i++) {
            if (dirs.includes(arr[i].direction)) lastIdx = i;
          }
          arr.splice(lastIdx + 1, 0, item);
        }

        config[key] = arr;
        saveConfig().catch(() => {});
      }
    }

    dragState = null;
  }

  // ── Modal state ───────────────────────────────────────────────────────────────
  /** @type {{ type: string, channelId: string }|null} */
  let activeModal = $state(null);

  function openModal(type, channelId) { activeModal = { type, channelId }; }
  function closeModal() { activeModal = null; }

  function findChannel(id) {
    return (config.mode === 'gaming' ? config.gaming_channels : config.streaming_channels)
      .find(c => c.id === id);
  }

  /**
   * @param {string} icon
   * @returns {Promise<string|null>}
   */
  async function resolveIconBase64(icon) {
    // Manifest PNG icons — plugin loads from bundled PNGs, no base64 needed
    if (icon && !icon.startsWith('ti-') && !icon.startsWith('brand:') &&
        !icon.startsWith('data:') && !icon.startsWith('http')) return null;

    // Old brand: format — still resolve for backward compat
    const brand = BRAND_ICONS[icon];
    if (!brand) return null;
    if (brand.svg) {
      const svgText = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">${brand.svg}</svg>`;
      return `data:image/svg+xml;base64,${btoa(svgText)}`;
    }
    if (brand.src) {
      try {
        const resp = await fetch(brand.src);
        const blob = await resp.blob();
        return await new Promise(resolve => {
          const reader = new FileReader();
          reader.onload = () => resolve(/** @type {string} */ (reader.result));
          reader.onerror = () => resolve(null);
          reader.readAsDataURL(blob);
        });
      } catch { return null; }
    }
    return null;
  }

  /** @param {string} id */
  async function broadcastAppearance(id) {
    const ch = findChannel(id);
    if (!ch) return;
    const customIconBase64 = await resolveIconBase64(ch.icon);
    invoke('broadcast_channel_appearance', {
      channelId:        ch.id,
      name:             ch.name,
      color:            ch.color,
      icon:             ch.icon,
      customIconBase64,
    }).catch(() => {});
  }

  /**
   * @param {string} id
   * @param {Partial<import('$lib/store.svelte.js').ChannelConfig>} patch
   */
  function updateChannel(id, patch) {
    const ch = findChannel(id);
    if (ch) Object.assign(ch, patch);
  }

  async function hotswapChannel(id) {
    if (!engineRunning.value) return;
    const ch = findChannel(id);
    if (ch) await restartEngineChannel(ch).catch(e => log('Hot-swap error: ' + e));
  }

  /** @type {string|null} */
  let pendingDelete = $state(null);

  function removeChannel(id) {
    pendingDelete = id;
  }

  function confirmDelete() {
    const id = pendingDelete;
    pendingDelete = null;
    if (!id) return;
    if (config.mode === 'gaming') {
      config.gaming_channels = config.gaming_channels.filter(c => c.id !== id);
    } else {
      config.streaming_channels = config.streaming_channels.filter(c => c.id !== id);
    }
  }

  /** @param {string} direction */
  function addChannel(direction) {
    const dirColors = { OUT: '#22c55e', IN: '#3b82f6', APP: '#a855f7', MIC: '#f59e0b', MICOUT: '#ec4899' };
    const dirIcons  = { OUT: 'ti-volume', IN: 'ti-headphones', APP: 'ti-device-laptop', MIC: 'ti-microphone', MICOUT: 'ti-headphones' };
    const dirNames  = { OUT: 'New Output', IN: 'New Input', APP: 'New App', MIC: 'New Mic In', MICOUT: 'New Mic Out' };
    const newCh = {
      id: crypto.randomUUID(),
      name: dirNames[direction] ?? 'New Channel',
      direction,
      device: '',
      port: 5000 + channels.length,
      volume: 100,
      color: dirColors[direction] ?? '#888',
      icon: dirIcons[direction] ?? 'ti-volume',
      enabled: true,
    };
    if (config.mode === 'gaming') {
      config.gaming_channels = [...config.gaming_channels, newCh];
    } else {
      config.streaming_channels = [...config.streaming_channels, newCh];
    }
  }

  function toggleChannel(id) {
    const ch = findChannel(id);
    if (ch) { ch.enabled = !ch.enabled; hotswapChannel(id); }
  }

  function switchMode() {
    config.mode = config.mode === 'gaming' ? 'streaming' : 'gaming';
  }

  // ── Context menu ──────────────────────────────────────────────────────────────
  /** @type {{ channelId: string, x: number, y: number }|null} */
  let contextMenu = $state(null);

  /** @param {MouseEvent} e @param {string} channelId */
  function openContextMenu(e, channelId) {
    const x = Math.min(e.clientX, window.innerWidth  - 190);
    const y = Math.min(e.clientY, window.innerHeight - 260);
    contextMenu = { channelId, x, y };
  }

  /** @param {string} action @param {string} channelId */
  function handleContextAction(action, channelId) {
    switch (action) {
      case 'rename':  openModal('name',   channelId); break;
      case 'device':  openModal('device', channelId); break;
      case 'type':    openModal('type',   channelId); break;
      case 'color':   openModal('color',  channelId); break;
      case 'icon':    openModal('icon',   channelId); break;
      case 'info':    openModal('info',   channelId); break;
      case 'toggle':  toggleChannel(channelId);       break;
      case 'delete':  removeChannel(channelId);       break;
    }
  }

  // ── App icon suggestion ───────────────────────────────────────────────────────
  const APP_ICON_MAP = /** @type {Record<string,string>} */ ({
    discord:   'brand:discord',
    spotify:   'brand:spotify',
    obs:       'brand:obs',
    obs64:     'brand:obs',
    obsstudio: 'brand:obs',
    chrome:    'ti-brand-chrome',
    firefox:   'ti-brand-firefox',
    opera:     'ti-brand-opera',
    steam:     'ti-brand-steam',
    vlc:       'ti-player-play',
    zoom:      'ti-video',
    slack:     'ti-brand-slack',
    teams:     'ti-brand-teams',
    skype:     'ti-brand-skype',
    brave:     'ti-brand-chrome',
    msedge:    'ti-browser',
    iexplore:  'ti-browser',
  });

  /** @param {string} processName */
  function suggestAppIcon(processName) {
    const key = processName.toLowerCase().replace(/\.exe$/i, '').replace(/[^a-z0-9]/g, '');
    return APP_ICON_MAP[key] ?? null;
  }

  // ── Panels ────────────────────────────────────────────────────────────────────
  let showSettings = $state(false);
  let showLog      = $state(false);
  let showPeerIp   = $state(false);
  let autostart    = $state(false);

  async function toggleAutostart() {
    autostart = !autostart;
    try { await invoke('set_autostart', { enabled: autostart }); }
    catch (e) { autostart = !autostart; log('Autostart error: ' + e); }
  }

  /** @type {string[]} */
  let logLines = $state([]);

  function log(msg) {
    const ts = new Date().toLocaleTimeString();
    logLines = [`[${ts}] ${msg}`, ...logLines].slice(0, 200);
  }

  async function handleStart(broadcast = true) {
    try {
      await startEngine();
      log('Engine started — routing to ' + destIp);
      if (broadcast) {
        const ip = peerStatus.ip ?? destIp;
        log('Sending start_all to peer: ' + (ip || '(no ip)'));
        if (ip) sendPeerCommand(ip, 'start_all').catch(e => log('Peer start cmd error: ' + e));
      }
    } catch (e) { log('Start error: ' + e); }
  }

  async function handleStop(broadcast = true) {
    try {
      await stopEngine();
      log('Engine stopped.');
      if (broadcast) {
        const ip = peerStatus.ip ?? destIp;
        log('Sending stop_all to peer: ' + (ip || '(no ip)'));
        if (ip) sendPeerCommand(ip, 'stop_all').catch(e => log('Peer stop cmd error: ' + e));
      }
    } catch (e) { log('Stop error: ' + e); }
  }

  async function handleSave() {
    try {
      await saveConfig();
      log('Config saved.');
    } catch (e) { log('Save error: ' + e); }
  }

  // ── Init ──────────────────────────────────────────────────────────────────────
  $effect(() => {
    loadConfig().then(() => { configLoaded = true; startMonitoring().catch(() => {}); }).catch(e => log('Load config error: ' + e));
    invoke('get_autostart').then(v => { autostart = /** @type {boolean} */ (v); }).catch(() => {});
    let unlisten = () => {};
    let unlistenLog = () => {};
    let unlistenErr = () => {};
    let unlistenPeer = () => {};
    setupListeners().then(fn => { unlisten = fn; }).catch(() => {});
    listen('engine-log',   e => log('[Engine] ' + e.payload.message)).then(fn => { unlistenLog = fn; }).catch(() => {});
    listen('engine-error', e => log('[Error]  ' + e.payload.message)).then(fn => { unlistenErr = fn; }).catch(() => {});
    listen('peer-command', e => {
      log('[Peer] received command: ' + e.payload.cmd);
      if (e.payload.cmd === 'start_all') handleStart(false);
      else if (e.payload.cmd === 'stop_all') handleStop(false);
    }).then(fn => { unlistenPeer = fn; }).catch(e => log('peer-command listen error: ' + e));
    return () => { unlisten(); unlistenLog(); unlistenErr(); unlistenPeer(); };
  });

  // ── Channel status derivation ─────────────────────────────────────────────────
  /** @param {string} id */
  function chStatus(id) {
    if (!engineRunning.value) return 'idle';
    const ch = findChannel(id);
    if (!ch?.enabled) return 'idle';
    return channelStatuses[id] ?? 'active';
  }

  // ── Helpers ───────────────────────────────────────────────────────────────────
  /** @param {number} v @param {number} min @param {number} max @param {number} step */
  function clampStep(v, min, max, step) {
    return Math.max(min, Math.min(max, Math.round(v / step) * step));
  }
</script>

<!-- ── Top bar ────────────────────────────────────────────────────────────────── -->
<header class="topbar">
  <div class="brand">
    <img src="/assets/shadowbridge_icon_64.png" width="32" height="32" style="object-fit: contain;" alt="" />
    <img src="/assets/shadowbridge_wordmark.png" height="22" style="object-fit: contain; width: auto;" alt="ShadowBridge" />
  </div>

  <div class="topbar-btns">
    <button class="tb-btn mode-btn" onclick={switchMode}>
      <span class="mode-dot"></span>
      {config.mode === 'gaming' ? 'Gaming PC' : 'Streaming PC'}
    </button>
    <button class="tb-btn" class:tb-active={showLog}
      onclick={() => { showLog = !showLog; showSettings = false; }}>Log</button>
    <button class="tb-btn" class:tb-active={showSettings}
      onclick={() => { showSettings = !showSettings; showLog = false; }}>Settings</button>
  </div>
</header>

<!-- ── Status bar ─────────────────────────────────────────────────────────────── -->
<div class="statusbar">
  <span class="peer-dot" class:connected={peerStatus.connected}></span>
  <span class="peer-text">
    {#if peerStatus.connected}
      Connected{peerStatus.mode ? ` (${peerStatus.mode})` : ''} —
      {#if showPeerIp}
        {peerStatus.ip ?? destIp}
      {:else}
        ●●●.●●●.●.●●●
      {/if}
    {:else}
      Searching for peer on {showPeerIp ? destIp : '●●●.●●●.●.●●●'}
    {/if}
  </span>
  <button class="eye-btn" onclick={() => showPeerIp = !showPeerIp} title="Toggle IP visibility">
    {showPeerIp ? '🙈' : '👁'}
  </button>
  {#if peerStatus.connected && peerStatus.ip && peerStatus.ip !== destIp}
    <button class="use-ip-btn" onclick={applyPeerIp} title="Fill destination IP with peer address">
      Use {peerStatus.ip}
    </button>
  {/if}
</div>

<!-- ── Settings panel ─────────────────────────────────────────────────────────── -->
{#if showSettings}
  <div class="side-panel">
    <div class="panel-head">
      <span>Settings</span>
      <button class="x-btn" onclick={() => showSettings = false}>✕</button>
    </div>
    <div class="panel-body">

      <!-- Network -->
      <div class="section-label">Network</div>
      <label class="field">
        <span class="field-label">
          Gaming PC IP
          <span class="tip" data-tip="LAN IP of the Gaming PC — used as destination when Streaming PC sends audio back">?</span>
        </span>
        <input class="field-input" type="text" value={config.gaming_ip}
          oninput={e => config.gaming_ip = e.currentTarget.value}
          placeholder="192.168.x.x" />
      </label>
      <label class="field">
        <span class="field-label">
          Streaming PC IP
          <span class="tip" data-tip="LAN IP of the Streaming PC — used as destination when Gaming PC sends audio">?</span>
        </span>
        <input class="field-input" type="text" value={config.streaming_ip}
          oninput={e => config.streaming_ip = e.currentTarget.value}
          placeholder="192.168.x.x" />
      </label>
      <label class="field">
        <span class="field-label">
          Discovery Port
          <span class="tip" data-tip="UDP port for peer discovery broadcasts (both PCs must match)">?</span>
        </span>
        <input class="field-input" type="number" min="1024" max="65535"
          value={config.discovery_port}
          oninput={e => config.discovery_port = clampStep(Number(e.currentTarget.value), 1024, 65535, 1)} />
      </label>
      <label class="field">
        <span class="field-label">
          Command Port
          <span class="tip" data-tip="Reserved for future remote control features">?</span>
        </span>
        <input class="field-input" type="number" min="1024" max="65535"
          value={config.command_port}
          oninput={e => config.command_port = clampStep(Number(e.currentTarget.value), 1024, 65535, 1)} />
      </label>

      <!-- Audio -->
      <div class="section-label" style="margin-top:8px">Audio</div>
      <label class="field">
        <span class="field-label">
          Buffer Size (samples)
          <span class="tip" data-tip="CPAL capture buffer size. Lower = less latency, higher = more stable. Requires engine restart.">?</span>
        </span>
        <input class="field-input" type="number" min="64" max="8192" step="64"
          value={config.buffer_size}
          oninput={e => config.buffer_size = clampStep(Number(e.currentTarget.value), 64, 8192, 64)} />
      </label>
      <label class="field">
        <span class="field-label">
          Sample Rate (Hz)
          <span class="tip" data-tip="Wire sample rate. WASAPI resamples internally. 48000 recommended.">?</span>
        </span>
        <input class="field-input" type="number" min="8000" max="192000" step="100"
          value={config.sample_rate}
          oninput={e => config.sample_rate = clampStep(Number(e.currentTarget.value), 8000, 192000, 100)} />
      </label>
      <label class="field">
        <span class="field-label">
          Buffer Offset (s)
          <span class="tip" data-tip="Pre-roll jitter buffer on playback side, in seconds. Higher = smoother audio over unstable networks.">?</span>
        </span>
        <input class="field-input" type="number" min="0" max="5" step="0.1"
          value={(config.buffer_offset_ms / 1000).toFixed(1)}
          oninput={e => config.buffer_offset_ms = Math.round(clampStep(Number(e.currentTarget.value), 0, 5, 0.1) * 1000)} />
      </label>

      <!-- Startup & Behavior -->
      <div class="section-label" style="margin-top:8px">Startup &amp; Behavior</div>
      <div class="field toggle-field">
        <span class="field-label">
          Launch at Login
          <span class="tip" data-tip="Start ShadowBridge automatically when Windows starts">?</span>
        </span>
        <button class="toggle-btn" class:on={autostart} onclick={toggleAutostart}
          aria-label="Toggle auto-start">
          <span class="toggle-knob"></span>
        </button>
      </div>
      <div class="field toggle-field">
        <span class="field-label">
          Auto-start Streams
          <span class="tip" data-tip="Start the engine automatically when a peer is detected">?</span>
        </span>
        <button class="toggle-btn" class:on={config.auto_start_streams}
          onclick={() => config.auto_start_streams = !config.auto_start_streams}
          aria-label="Toggle auto-start streams">
          <span class="toggle-knob"></span>
        </button>
      </div>
      <div class="field toggle-field">
        <span class="field-label">
          Start Minimized
          <span class="tip" data-tip="Launch to system tray instead of showing the window">?</span>
        </span>
        <button class="toggle-btn" class:on={config.start_minimized}
          onclick={() => config.start_minimized = !config.start_minimized}
          aria-label="Toggle start minimized">
          <span class="toggle-knob"></span>
        </button>
      </div>
      <div class="field toggle-field">
        <span class="field-label">
          Run in Background
          <span class="tip" data-tip="Hide to system tray instead of quitting when the window is closed">?</span>
        </span>
        <button class="toggle-btn" class:on={config.tray_on_close}
          onclick={() => config.tray_on_close = !config.tray_on_close}
          aria-label="Toggle run in background">
          <span class="toggle-knob"></span>
        </button>
      </div>

      <!-- Notifications -->
      <div class="section-label" style="margin-top:8px">Notifications</div>
      <div class="field toggle-field">
        <span class="field-label">
          Peer Events
          <span class="tip" data-tip="Notify when a peer connects or disconnects">?</span>
        </span>
        <button class="toggle-btn" class:on={config.notify_peer_events}
          onclick={() => config.notify_peer_events = !config.notify_peer_events}
          aria-label="Toggle peer event notifications">
          <span class="toggle-knob"></span>
        </button>
      </div>
      <div class="field toggle-field">
        <span class="field-label">
          Channel Errors
          <span class="tip" data-tip="Notify when a channel encounters an audio error">?</span>
        </span>
        <button class="toggle-btn" class:on={config.notify_channel_errors}
          onclick={() => config.notify_channel_errors = !config.notify_channel_errors}
          aria-label="Toggle channel error notifications">
          <span class="toggle-knob"></span>
        </button>
      </div>

      <button class="save-btn" onclick={handleSave}>Save Config</button>
    </div>
  </div>
{/if}

<!-- ── Log panel ──────────────────────────────────────────────────────────────── -->
{#if showLog}
  <div class="side-panel log-panel">
    <div class="panel-head">
      <span>Log</span>
      <button class="x-btn" onclick={() => showLog = false}>✕</button>
    </div>
    <div class="log-body">
      {#if logLines.length === 0}
        <span class="log-empty">No log entries.</span>
      {:else}
        {#each logLines as line}
          <div class="log-line">{line}</div>
        {/each}
      {/if}
    </div>
  </div>
{/if}

<!-- ── Main scrollable area ───────────────────────────────────────────────────── -->
<main class="main">
  <div class="strips-row"
    bind:this={stripsRowEl}
    onpointermove={onPointerMove}
    onpointerup={onPointerUp}
  >
    <!-- OUTGOING section -->
    <div class="section-div">
      <div class="div-line"></div>
      <span class="div-label" style="color:#22c55e">OUTGOING</span>
      <div class="div-line"></div>
      <button class="add-btn" style="color:#22c55e;border-color:#22c55e66" onclick={() => addChannel('OUT')} title="Add output channel">+</button>
    </div>
    <div data-section="out" style="display:contents">
      {#each outgoing as ch (ch.id)}
        <ChannelStrip
          channel={ch}
          level={channelLevels[ch.id] ?? 0}
          status={chStatus(ch.id)}
          onIconClick={() => openModal('icon', ch.id)}
          onColorClick={() => openModal('color', ch.id)}
          onNameClick={() => openModal('name', ch.id)}
          onTypeClick={() => openModal('type', ch.id)}
          onDeviceClick={() => openModal('device', ch.id)}
          onToggle={() => toggleChannel(ch.id)}
          onDelete={() => removeChannel(ch.id)}
          onVolumeChange={v => { updateChannel(ch.id, { volume: v }); setChannelVolume(ch.id, v); }}
          onContextMenu={e => openContextMenu(e, ch.id)}
          onChannelPointerDown={e => onPointerDown(e, ch.id, 'out')}
        />
      {/each}
    </div>

    <!-- INCOMING section -->
    <div class="section-div">
      <div class="div-line"></div>
      <span class="div-label" style="color:#3b82f6">INCOMING</span>
      <div class="div-line"></div>
      <button class="add-btn" style="color:#3b82f6;border-color:#3b82f666" onclick={() => addChannel('IN')} title="Add input channel">+</button>
    </div>
    <div data-section="in" style="display:contents">
      {#each incoming as ch (ch.id)}
        <ChannelStrip
          channel={ch}
          level={channelLevels[ch.id] ?? 0}
          status={chStatus(ch.id)}
          onIconClick={() => openModal('icon', ch.id)}
          onColorClick={() => openModal('color', ch.id)}
          onNameClick={() => openModal('name', ch.id)}
          onTypeClick={() => openModal('type', ch.id)}
          onDeviceClick={() => openModal('device', ch.id)}
          onToggle={() => toggleChannel(ch.id)}
          onDelete={() => removeChannel(ch.id)}
          onVolumeChange={v => { updateChannel(ch.id, { volume: v }); setChannelVolume(ch.id, v); }}
          onContextMenu={e => openContextMenu(e, ch.id)}
          onChannelPointerDown={e => onPointerDown(e, ch.id, 'in')}
        />
      {/each}
    </div>

    <!-- MIC INPUTS section -->
    <div class="section-div">
      <div class="div-line"></div>
      <span class="div-label" style="color:#f59e0b">MIC INPUTS</span>
      <div class="div-line"></div>
      <button class="add-btn" style="color:#f59e0b;border-color:#f59e0b66" onclick={() => addChannel('MIC')} title="Add mic input channel">+</button>
    </div>
    <div data-section="mic" style="display:contents">
      {#each micInputs as ch (ch.id)}
        <ChannelStrip
          channel={ch}
          level={channelLevels[ch.id] ?? 0}
          status={chStatus(ch.id)}
          onIconClick={() => openModal('icon', ch.id)}
          onColorClick={() => openModal('color', ch.id)}
          onNameClick={() => openModal('name', ch.id)}
          onTypeClick={() => openModal('type', ch.id)}
          onDeviceClick={() => openModal('device', ch.id)}
          onToggle={() => toggleChannel(ch.id)}
          onDelete={() => removeChannel(ch.id)}
          onVolumeChange={v => { updateChannel(ch.id, { volume: v }); setChannelVolume(ch.id, v); }}
          onContextMenu={e => openContextMenu(e, ch.id)}
          onChannelPointerDown={e => onPointerDown(e, ch.id, 'mic')}
        />
      {/each}
    </div>

    <!-- MIC OUTPUTS section -->
    <div class="section-div">
      <div class="div-line"></div>
      <span class="div-label" style="color:#e879f9">MIC OUTPUTS</span>
      <div class="div-line"></div>
      <button class="add-btn" style="color:#e879f9;border-color:#e879f966" onclick={() => addChannel('MICOUT')} title="Add mic output channel">+</button>
    </div>
    <div data-section="micout" style="display:contents">
      {#each micOut as ch (ch.id)}
        <ChannelStrip
          channel={ch}
          level={channelLevels[ch.id] ?? 0}
          status={chStatus(ch.id)}
          onIconClick={() => openModal('icon', ch.id)}
          onColorClick={() => openModal('color', ch.id)}
          onNameClick={() => openModal('name', ch.id)}
          onTypeClick={() => openModal('type', ch.id)}
          onDeviceClick={() => openModal('device', ch.id)}
          onToggle={() => toggleChannel(ch.id)}
          onDelete={() => removeChannel(ch.id)}
          onVolumeChange={v => { updateChannel(ch.id, { volume: v }); setChannelVolume(ch.id, v); }}
          onContextMenu={e => openContextMenu(e, ch.id)}
          onChannelPointerDown={e => onPointerDown(e, ch.id, 'micout')}
        />
      {/each}
    </div>
  </div>
</main>

<!-- ── Bottom bar ─────────────────────────────────────────────────────────────── -->
<footer class="bottom-bar">
  <button class="start-btn" onclick={handleStart} disabled={engineRunning.value}>
    ▶ Start All
  </button>
  <button class="stop-btn" onclick={handleStop} disabled={!engineRunning.value}>
    ■ Stop All
  </button>
</footer>

<!-- ── Sys bar ─────────────────────────────────────────────────────────────────── -->
<div class="sysbar">
  <span>{appVersion}</span>
  <span class="sys-status">SYS: {engineRunning.value ? 'RUNNING' : 'NOMINAL'}</span>
</div>

<!-- ── Engine error toast ──────────────────────────────────────────────────────── -->
{#if engineError.visible}
  <div class="error-toast" role="alert">
    <span>⚠ {engineError.message}</span>
    <button onclick={clearEngineError}>✕</button>
  </div>
{/if}

<!-- ── Context menu ────────────────────────────────────────────────────────────── -->
{#if contextMenu}
  {@const _ch = findChannel(contextMenu.channelId)}
  <ContextMenu
    x={contextMenu.x}
    y={contextMenu.y}
    channelEnabled={_ch?.enabled ?? true}
    onAction={action => handleContextAction(action, contextMenu?.channelId ?? '')}
    onClose={() => contextMenu = null}
  />
{/if}

<!-- ── Modals ──────────────────────────────────────────────────────────────────── -->
{#if activeModal?.type === 'icon'}
  {@const ch = findChannel(activeModal.channelId)}
  {#if ch}
    <IconPicker
      color={ch.color}
      currentIcon={ch.icon}
      onSelect={async icon => {
        const mid = activeModal?.channelId ?? '';
        const custom_icon_base64 = await resolveIconBase64(icon);
        updateChannel(mid, { icon, custom_icon_base64 });
        broadcastAppearance(mid);
        saveConfig();
      }}
      onClose={closeModal}
    />
  {/if}
{:else if activeModal?.type === 'color'}
  {@const ch = findChannel(activeModal.channelId)}
  {#if ch}
    <ColorPicker
      currentColor={ch.color}
      onChange={color => { const mid = activeModal?.channelId ?? ''; updateChannel(mid, { color }); broadcastAppearance(mid); }}
      onClose={closeModal}
    />
  {/if}
{:else if activeModal?.type === 'name'}
  {@const ch = findChannel(activeModal.channelId)}
  {#if ch}
    <NameEditor
      currentName={ch.name}
      onSave={name => { const mid = activeModal?.channelId ?? ''; updateChannel(mid, { name }); broadcastAppearance(mid); }}
      onClose={closeModal}
    />
  {/if}
{:else if activeModal?.type === 'type'}
  {@const ch = findChannel(activeModal.channelId)}
  {#if ch}
    <TypePicker
      currentType={ch.direction}
      onSelect={direction => {
        const mid = activeModal?.channelId ?? '';
        updateChannel(mid, { direction });
        hotswapChannel(mid);
      }}
      onClose={closeModal}
    />
  {/if}
{:else if activeModal?.type === 'device'}
  {@const ch = findChannel(activeModal.channelId)}
  {#if ch}
    <DevicePicker
      direction={ch.direction}
      currentDevice={ch.device}
      onSelect={device => {
        const mid = activeModal?.channelId ?? '';
        updateChannel(mid, { device });
        if (ch.direction === 'APP') {
          const suggested = suggestAppIcon(device);
          if (suggested) updateChannel(mid, { icon: suggested });
        }
        hotswapChannel(mid);
      }}
      onClose={closeModal}
    />
  {/if}
{:else if activeModal?.type === 'info'}
  {@const ch = findChannel(activeModal.channelId)}
  {#if ch}
    <ChannelInfo
      channel={ch}
      status={chStatus(ch.id)}
      onClose={closeModal}
      onPortChange={port => { updateChannel(ch.id, { port }); saveConfig(); hotswapChannel(ch.id); }}
    />
  {/if}
{/if}

<!-- ── Delete confirmation ─────────────────────────────────────────────────────── -->
{#if pendingDelete}
  {@const ch = findChannel(pendingDelete)}
  <div class="confirm-backdrop" role="dialog" aria-modal="true">
    <div class="confirm-box">
      <p class="confirm-msg">Delete <strong>{ch?.name ?? 'this channel'}</strong>?</p>
      <p class="confirm-sub">This cannot be undone.</p>
      <div class="confirm-btns">
        <button class="confirm-cancel" onclick={() => pendingDelete = null}>Cancel</button>
        <button class="confirm-ok" onclick={confirmDelete}>Delete</button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* ── Reset ──────────────────────────────────────────────────────────────────── */
  :global(*, *::before, *::after) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(html, body) {
    height: 100%; width: 100%;
    overflow: hidden;
    background: #0d1117;
    color: #e6edf3;
    font-family: 'Figtree', system-ui, sans-serif;
    font-size: 13px;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Shell layout ───────────────────────────────────────────────────────────── */
  .topbar {
    position: fixed; top: 0; left: 0; right: 0; height: 44px;
    background: #090d13;
    border-bottom: 1px solid #21262d;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 14px;
    z-index: 100;
  }

  .statusbar {
    position: fixed; top: 44px; left: 0; right: 0; height: 30px;
    background: #090d13;
    border-bottom: 1px solid #21262d;
    display: flex; align-items: center; gap: 7px;
    padding: 0 14px;
    z-index: 100;
  }

  .main {
    position: fixed;
    top: 74px; left: 0; right: 0;
    bottom: 64px;
    overflow-x: auto; overflow-y: hidden;
    background: #0d1117;
    display: flex;
    align-items: stretch;
  }

  .bottom-bar {
    position: fixed; bottom: 24px; left: 0; right: 0; height: 40px;
    background: #090d13;
    border-top: 1px solid #21262d;
    display: flex; align-items: center; gap: 8px;
    padding: 0 16px;
    z-index: 100;
  }

  .sysbar {
    position: fixed; bottom: 0; left: 0; right: 0; height: 24px;
    background: #060a10;
    border-top: 1px solid #21262d;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 12px;
    font-size: 10px; color: #444;
    font-family: monospace;
    z-index: 100;
  }
  .sys-status { color: #22c55e; }

  /* ── Brand ──────────────────────────────────────────────────────────────────── */
  .brand { display: flex; align-items: center; gap: 9px; }

  /* ── Topbar buttons ─────────────────────────────────────────────────────────── */
  .topbar-btns { display: flex; gap: 6px; }
  .tb-btn {
    height: 28px; padding: 0 14px;
    border-radius: 6px;
    border: 1px solid #30363d;
    background: #21262d; color: #8b949e;
    font-size: 11px; font-weight: 600;
    font-family: 'Figtree', sans-serif;
    cursor: pointer; white-space: nowrap;
    transition: all 0.15s;
  }
  .tb-btn:hover { background: #30363d; color: #e6edf3; }
  .tb-btn.tb-active { background: #30363d; color: #e6edf3; border-color: #484f58; }
  .mode-btn {
    background: #0f2b0f; border-color: #22c55e55; color: #22c55e;
    display: flex; align-items: center; gap: 6px;
  }
  .mode-btn:hover { background: #163d16; }
  .mode-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 6px #22c55e;
    animation: pulse 2s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

  /* ── Status bar ─────────────────────────────────────────────────────────────── */
  .peer-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #333; flex-shrink: 0;
    transition: background 0.3s;
  }
  .peer-dot.connected { background: #22c55e; box-shadow: 0 0 5px #22c55e44; }
  .peer-text { font-size: 11px; color: #555; flex: 1; }
  .eye-btn {
    background: none; border: none; cursor: pointer; font-size: 13px;
    opacity: 0.5; transition: opacity 0.15s;
  }
  .eye-btn:hover { opacity: 1; }

  .use-ip-btn {
    margin-left: 6px; padding: 1px 7px; border-radius: 4px; font-size: 11px;
    background: #0d2018; color: #3fb950; border: 1px solid #1e4228;
    cursor: pointer; transition: background 0.15s;
  }
  .use-ip-btn:hover { background: #152d20; }

  /* ── Side panel ─────────────────────────────────────────────────────────────── */
  .side-panel {
    position: fixed; top: 74px; right: 0; bottom: 64px; width: 260px;
    background: #090d13;
    border-left: 1px solid #21262d;
    z-index: 90;
    display: flex; flex-direction: column;
  }
  .panel-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px;
    border-bottom: 1px solid #21262d;
    font-size: 12px; font-weight: 700; color: #8b949e;
  }
  .x-btn { background: none; border: none; color: #555; cursor: pointer; font-size: 13px; }
  .x-btn:hover { color: #ef4444; }
  .panel-body {
    flex: 1; padding: 14px;
    display: flex; flex-direction: column; gap: 10px;
    overflow-y: auto;
  }
  .section-label {
    font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    color: #444; padding-bottom: 2px; border-bottom: 1px solid #21262d;
    font-family: 'Figtree', sans-serif;
  }
  .field { display: flex; flex-direction: column; gap: 3px; }
  .field-label {
    font-size: 10px; color: #555; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; display: flex; align-items: center; gap: 4px;
  }
  .tip {
    display: inline-flex; align-items: center; justify-content: center;
    width: 13px; height: 13px; border-radius: 50%;
    background: #21262d; color: #555; font-size: 8px; font-weight: 700;
    cursor: default; position: relative; flex-shrink: 0;
  }
  .tip::after {
    content: attr(data-tip);
    position: absolute; bottom: calc(100% + 6px); left: 50%; transform: translateX(-50%);
    background: #161b22; border: 1px solid #30363d; border-radius: 5px;
    color: #c9d1d9; font-size: 10px; font-weight: 400; letter-spacing: 0; text-transform: none;
    white-space: normal; width: 180px; padding: 6px 8px; line-height: 1.4;
    opacity: 0; pointer-events: none;
    transition: opacity 0.15s;
    z-index: 500;
  }
  .tip:hover::after { opacity: 1; }
  .field-input {
    padding: 5px 8px;
    background: #0d1117; border: 1px solid #30363d;
    border-radius: 5px; color: #e6edf3; font-size: 12px;
    font-family: 'Figtree', sans-serif;
  }
  .field-input:focus { outline: none; border-color: #388bfd; }
  .save-btn {
    margin-top: 4px; padding: 6px 16px;
    background: #238636; border: 1px solid #2ea043;
    border-radius: 5px; color: #fff; font-size: 11px; font-weight: 700;
    cursor: pointer; font-family: 'Figtree', sans-serif;
    align-self: flex-end;
  }
  .save-btn:hover { background: #2ea043; }

  .toggle-field { flex-direction: row; align-items: center; justify-content: space-between; }
  .toggle-btn {
    width: 36px; height: 20px; border-radius: 10px; border: none; cursor: pointer;
    background: #30363d; position: relative; transition: background 0.2s; flex-shrink: 0;
  }
  .toggle-btn.on { background: #2ea043; }
  .toggle-knob {
    position: absolute; top: 3px; left: 3px; width: 14px; height: 14px;
    border-radius: 50%; background: #fff; transition: left 0.2s;
  }
  .toggle-btn.on .toggle-knob { left: 19px; }
  .log-panel .panel-body { display: block; padding: 0; }
  .log-body {
    flex: 1; overflow-y: auto; padding: 8px;
    font-size: 10px; font-family: 'Consolas', monospace;
    color: #555; display: flex; flex-direction: column; gap: 1px;
  }
  .log-empty { color: #333; font-style: italic; padding: 12px; }
  .log-line { color: #8b949e; line-height: 1.4; }

  /* ── Channel strips row ─────────────────────────────────────────────────────── */
  .strips-row {
    display: flex;
    flex-direction: row;
    align-items: stretch;
    gap: 8px;
    padding: 14px 18px;
    min-width: max-content;
    flex: 1;
  }

  :global(.drag-insert-before) {
    border-left: 2px solid #58a6ff !important;
    margin-left: -2px;
  }

  /* ── Section dividers ───────────────────────────────────────────────────────── */
  .section-div {
    display: flex;
    flex-direction: column;
    align-items: center;
    align-self: stretch;
    gap: 5px;
    width: 22px;
    flex-shrink: 0;
    padding: 6px 0;
  }
  .div-line { flex: 1; width: 1px; background: #21262d; }
  .div-label {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    font-size: 11px; font-weight: 700;
    letter-spacing: 0.1em;
    opacity: 0.75;
    text-transform: uppercase;
    white-space: nowrap;
    font-family: 'Oxanium', sans-serif;
    transition: opacity 0.15s;
  }
  .section-div:hover .div-label { opacity: 1; }

  /* ── Add channel button (inside section divider) ────────────────────────────── */
  .add-btn {
    width: 24px; height: 24px;
    border-radius: 5px;
    border: 1px solid;
    background: color-mix(in srgb, currentColor 20%, transparent);
    font-size: 14px; font-weight: 700; font-family: monospace; line-height: 1;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    padding: 0;
    flex-shrink: 0;
    transition: background 0.15s;
  }
  .add-btn:hover { background: color-mix(in srgb, currentColor 40%, transparent); }

  /* ── Bottom bar ─────────────────────────────────────────────────────────────── */
  .start-btn, .stop-btn {
    flex: 1;
    padding: 10px;
    border-radius: 7px;
    font-size: 11px; font-weight: 700;
    letter-spacing: 0.06em;
    cursor: pointer;
    font-family: 'Figtree', sans-serif;
    transition: background 0.12s;
  }
  .start-btn { background: #0d2018; color: #3fb950; border: 1px solid #1e4228; }
  .start-btn:hover:not(:disabled) { background: #112a1e; }
  .start-btn:disabled { opacity: 0.45; cursor: not-allowed; }
  .stop-btn { background: #1e1014; color: #ff6b6b; border: 1px solid #3a1e1a; }
  .stop-btn:hover:not(:disabled) { background: #2d1018; }
  .stop-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .error-toast {
    position: fixed; bottom: 52px; left: 50%; transform: translateX(-50%);
    display: flex; align-items: center; gap: 10px;
    background: #2d1018; color: #ff6b6b; border: 1px solid #7f1d1d;
    border-radius: 7px; padding: 8px 14px; font-size: 13px;
    box-shadow: 0 4px 16px #0008; z-index: 999;
    animation: toast-in 0.2s ease;
  }
  .error-toast button {
    background: none; border: none; color: #ff6b6b; cursor: pointer;
    font-size: 14px; opacity: 0.7; padding: 0;
  }
  .error-toast button:hover { opacity: 1; }
  @keyframes toast-in { from { opacity: 0; transform: translateX(-50%) translateY(8px); } }

  /* ── Delete confirmation ─────────────────────────────────────────────────────── */
  .confirm-backdrop {
    position: fixed; inset: 0;
    background: #00000088;
    display: flex; align-items: center; justify-content: center;
    z-index: 1000;
    animation: toast-in 0.15s ease;
  }
  .confirm-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 22px 26px;
    display: flex; flex-direction: column; gap: 6px;
    min-width: 220px; max-width: 300px;
    box-shadow: 0 8px 32px #000a;
  }
  .confirm-msg {
    font-size: 14px; color: #e6edf3;
    font-family: 'Figtree', sans-serif;
  }
  .confirm-msg strong { color: #fff; }
  .confirm-sub {
    font-size: 11px; color: #555;
    font-family: 'Figtree', sans-serif;
    margin-bottom: 6px;
  }
  .confirm-btns { display: flex; gap: 8px; justify-content: flex-end; }
  .confirm-cancel {
    padding: 6px 14px; border-radius: 6px;
    border: 1px solid #30363d; background: #21262d;
    color: #8b949e; font-size: 12px; font-weight: 600;
    font-family: 'Figtree', sans-serif; cursor: pointer;
    transition: background 0.12s;
  }
  .confirm-cancel:hover { background: #30363d; color: #e6edf3; }
  .confirm-ok {
    padding: 6px 14px; border-radius: 6px;
    border: 1px solid #7f1d1d; background: #2d1018;
    color: #ff6b6b; font-size: 12px; font-weight: 600;
    font-family: 'Figtree', sans-serif; cursor: pointer;
    transition: background 0.12s;
  }
  .confirm-ok:hover { background: #3d1520; }
</style>
