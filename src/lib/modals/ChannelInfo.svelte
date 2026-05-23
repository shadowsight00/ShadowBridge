<script>
  /**
   * @type {{
   *   channel: import('../store.svelte.js').ChannelConfig,
   *   status?: string,
   *   onClose?: () => void,
   *   onPortChange?: (port: number) => void,
   * }}
   */
  let { channel, status = 'idle', onClose, onPortChange } = $props();

  const DIR_LABELS = { OUT: 'Loopback Out', IN: 'Audio In', APP: 'App Capture', MIC: 'Mic In', MICOUT: 'Mic Out' };
  const DIR_COLORS = { OUT: '#22c55e', IN: '#3b82f6', APP: '#a855f7', MIC: '#f59e0b', MICOUT: '#ec4899' };

  const dirLabel = $derived(DIR_LABELS[channel.direction] ?? channel.direction);
  const dirColor = $derived(DIR_COLORS[channel.direction] ?? '#888');

  let portValue = $state(String(channel.port));
  let portError = $state('');

  function applyPort() {
    const n = parseInt(portValue, 10);
    if (isNaN(n) || n < 1024 || n > 65535) {
      portError = 'Port must be 1024–65535';
      return;
    }
    portError = '';
    onPortChange?.(n);
  }

  /** @param {KeyboardEvent} e */
  function onPortKey(e) {
    if (e.key === 'Enter') applyPort();
    if (e.key === 'Escape') { portValue = String(channel.port); portError = ''; }
  }
</script>

<div class="overlay" onclick={e => { if (e.target === e.currentTarget) onClose?.(); }}>
  <div class="modal">
    <div class="modal-head">
      <span class="modal-title">Channel Info</span>
      <button class="x-btn" onclick={onClose}>✕</button>
    </div>
    <div class="body">
      <div class="row">
        <span class="lbl">Name</span>
        <span class="val">{channel.name}</span>
      </div>
      <div class="row">
        <span class="lbl">Direction</span>
        <span class="val" style="color:{dirColor}">{dirLabel}</span>
      </div>
      <div class="row">
        <span class="lbl">Device</span>
        <span class="val mono">{channel.device || '—'}</span>
      </div>

      <!-- Editable port row -->
      <div class="row port-row">
        <span class="lbl">Port</span>
        <div class="port-edit">
          <input
            class="port-input"
            class:err={!!portError}
            type="number"
            min="1024" max="65535"
            value={portValue}
            oninput={e => { portValue = e.currentTarget.value; portError = ''; }}
            onblur={applyPort}
            onkeydown={onPortKey}
          />
          <button class="port-apply" onclick={applyPort} title="Apply port">✔</button>
        </div>
      </div>
      {#if portError}
        <div class="port-err">{portError}</div>
      {/if}

      <div class="row">
        <span class="lbl">Volume</span>
        <span class="val">{channel.volume}%</span>
      </div>
      <div class="row">
        <span class="lbl">Status</span>
        <span class="val">{channel.enabled ? status : 'disabled'}</span>
      </div>
      <div class="row">
        <span class="lbl">ID</span>
        <span class="val mono small">{channel.id}</span>
      </div>
      <div class="color-preview" style="background:{channel.color}22;border-color:{channel.color}55">
        <span style="color:{channel.color};font-weight:700;font-size:11px">{channel.color}</span>
      </div>
    </div>
    <div class="footer">
      <button class="close-btn" onclick={onClose}>Close</button>
    </div>
  </div>
</div>

<style>
@keyframes overlay-fade { from { opacity:0 } to { opacity:1 } }
@keyframes modal-in { from { opacity:0;transform:scale(0.95) translateY(-8px) } to { opacity:1;transform:scale(1) translateY(0) } }
.overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.65);
  z-index: 300;
  display: flex; align-items: center; justify-content: center;
  animation: overlay-fade 0.15s ease;
}
.modal {
  background: #0d1117;
  border: 1px solid #21262d;
  border-radius: 10px;
  animation: modal-in 0.18s cubic-bezier(0.16,1,0.3,1);
  width: 280px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.6);
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px 10px;
  border-bottom: 1px solid #21262d;
}
.modal-title { font-size: 13px; font-weight: 700; color: #e6edf3; font-family: 'Figtree', sans-serif; }
.x-btn { background: none; border: none; color: #555; font-size: 14px; cursor: pointer; }
.x-btn:hover { color: #ef4444; }
.body { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.lbl { font-size: 10px; color: #555; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; flex-shrink: 0; }
.val { font-size: 12px; color: #c9d1d9; font-family: 'Figtree', sans-serif; text-align: right; }
.mono { font-family: monospace; font-size: 11px; }
.small { font-size: 9px; color: #555; }

.port-row { align-items: center; }
.port-edit { display: flex; align-items: center; gap: 4px; }
.port-input {
  width: 72px;
  padding: 3px 6px;
  background: #090d13;
  border: 1px solid #30363d;
  border-radius: 4px;
  color: #e6edf3;
  font-size: 12px;
  font-family: monospace;
  text-align: right;
}
.port-input:focus { outline: none; border-color: #388bfd; }
.port-input.err { border-color: #ef4444; }
.port-apply {
  width: 22px; height: 22px;
  background: #21262d; border: 1px solid #30363d;
  border-radius: 4px; color: #3fb950; font-size: 12px;
  cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0;
}
.port-apply:hover { background: #2d4a2d; border-color: #3fb950; }
.port-err { font-size: 10px; color: #ef4444; font-family: monospace; text-align: right; }

.color-preview {
  border: 1px solid; border-radius: 6px; padding: 6px 10px;
  text-align: center; margin-top: 2px;
}
.footer {
  display: flex; justify-content: flex-end;
  padding: 10px 16px 14px;
  border-top: 1px solid #21262d;
}
.close-btn {
  padding: 5px 16px;
  background: #21262d; border: 1px solid #30363d;
  border-radius: 5px; color: #8b949e; font-size: 11px; cursor: pointer;
  font-family: 'Figtree', sans-serif;
}
.close-btn:hover { color: #e6edf3; }
</style>
