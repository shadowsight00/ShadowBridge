<script>
  import { invoke } from '@tauri-apps/api/core';

  /**
   * @type {{
   *   direction?: string,
   *   currentDevice?: string,
   *   onSelect?: (device: string) => void,
   *   onClose?: () => void,
   * }}
   */
  let { direction = 'OUT', currentDevice = '', onSelect, onClose } = $props();

  /** @type {string[]} */
  let devices = $state([]);
  let loading = $state(true);
  let error = $state('');

  const commandMap = {
    OUT:    'get_loopback_devices',
    IN:     'get_output_devices',
    MIC:    'get_output_devices',
    MICOUT: 'get_input_devices',
    APP:    'get_app_audio_sources',
  };

  const labelMap = {
    OUT:    'Loopback Devices',
    IN:     'Output Devices',
    MIC:    'Output Devices',
    MICOUT: 'Input Devices',
    APP:    'App Audio Sources',
  };

  let refreshTick = $state(0);

  function refresh() { refreshTick++; }

  $effect(() => {
    // Re-runs on direction change or manual refresh.
    void refreshTick;
    const cmd = commandMap[direction] ?? 'get_output_devices';
    loading = true;
    error = '';
    invoke(cmd)
      .then(/** @param {string[]} list */ list => { devices = list; loading = false; })
      .catch(/** @param {unknown} e */ e => { error = String(e); loading = false; });
  });

  /** @param {string} d */
  function pick(d) { onSelect?.(d); onClose?.(); }
</script>

<div class="overlay" onclick={e => { if (e.target === e.currentTarget) onClose?.(); }}>
  <div class="modal">
    <div class="modal-head">
      <span class="modal-title">{labelMap[direction] ?? 'Devices'}</span>
      <div class="head-btns">
        <button class="refresh-btn" onclick={refresh} title="Refresh list" disabled={loading}>↻</button>
        <button class="x-btn" onclick={onClose}>✕</button>
      </div>
    </div>

    <div class="list-wrap">
      {#if loading}
        <div class="placeholder">Loading…</div>
      {:else if error}
        <div class="placeholder err">{error}</div>
      {:else if devices.length === 0}
        <div class="placeholder">No devices found.</div>
      {:else}
        {#each devices as d}
          <button
            class="device-row"
            class:selected={d === currentDevice}
            onclick={() => pick(d)}
          >
            <span class="check">{d === currentDevice ? '✔' : ''}</span>
            <span class="dev-name">{d}</span>
          </button>
        {/each}
      {/if}
    </div>
  </div>
</div>

<style>
@keyframes overlay-fade { from { opacity:0 } to { opacity:1 } }
@keyframes modal-in { from { opacity:0;transform:scale(0.95) translateY(-8px) } to { opacity:1;transform:scale(1) translateY(0) } }
.overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.65);
  animation: overlay-fade 0.15s ease;
  z-index: 300;
  display: flex; align-items: center; justify-content: center;
}
.modal {
  background: #0d1117;
  border: 1px solid #21262d;
  border-radius: 10px;
  animation: modal-in 0.18s cubic-bezier(0.16,1,0.3,1);
  width: 340px;
  max-height: 75vh;
  display: flex; flex-direction: column;
  box-shadow: 0 16px 48px rgba(0,0,0,0.6);
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px 10px;
  border-bottom: 1px solid #21262d;
  flex-shrink: 0;
}
.modal-title { font-size: 13px; font-weight: 700; color: #e6edf3; font-family: 'Figtree', sans-serif; }
.head-btns { display: flex; align-items: center; gap: 4px; }
.refresh-btn {
  background: none; border: none; color: #555; font-size: 16px; cursor: pointer;
  line-height: 1; padding: 0 4px; transition: color 0.15s, transform 0.2s;
}
.refresh-btn:hover:not(:disabled) { color: #3fb950; transform: rotate(90deg); }
.refresh-btn:disabled { opacity: 0.3; cursor: default; }
.x-btn { background: none; border: none; color: #555; font-size: 14px; cursor: pointer; }
.x-btn:hover { color: #ef4444; }
.list-wrap { overflow-y: auto; flex: 1; padding: 6px; }
.placeholder {
  padding: 24px; text-align: center;
  font-size: 12px; color: #555;
  font-family: 'Figtree', sans-serif;
}
.placeholder.err { color: #ef4444; }
.device-row {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 8px 10px;
  border-radius: 5px; border: none;
  background: none; cursor: pointer;
  text-align: left;
  transition: background 0.12s;
}
.device-row:hover { background: #21262d; }
.device-row.selected { background: #21262d; }
.check { width: 14px; font-size: 11px; color: #22c55e; flex-shrink: 0; }
.dev-name { font-size: 11px; color: #e6edf3; font-family: 'Figtree', sans-serif; }
</style>
