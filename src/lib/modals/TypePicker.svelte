<script>
  let { currentType = 'OUT', onSelect, onClose } = $props();

  const TYPES = [
    { id: 'OUT',    label: 'Loopback Out', sub: 'System audio → peer',    color: '#22c55e', icon: '🔊' },
    { id: 'IN',     label: 'Audio In',     sub: 'Receive audio → speaker', color: '#3b82f6', icon: '🎧' },
    { id: 'APP',    label: 'App Capture',  sub: 'App process → peer',      color: '#a855f7', icon: '🖥' },
    { id: 'MIC',    label: 'MIC IN',       sub: 'Receive mic → output',    color: '#f59e0b', icon: '🎤' },
    { id: 'MICOUT', label: 'MIC OUT',      sub: 'Mic capture → peer',      color: '#ec4899', icon: '🎙' },
  ];

  /** @param {string} id */
  function pick(id) { onSelect?.(id); onClose?.(); }
</script>

<div class="overlay" onclick={e => { if (e.target === e.currentTarget) onClose?.(); }}>
  <div class="modal">
    <div class="modal-head">
      <span class="modal-title">Channel Type</span>
      <button class="x-btn" onclick={onClose}>✕</button>
    </div>
    <div class="grid">
      {#each TYPES as t}
        <button
          class="type-cell"
          class:active={t.id === currentType}
          style={t.id === currentType ? `border-color:${t.color};background:${t.color}18` : ''}
          onclick={() => pick(t.id)}
        >
          <span class="type-icon">{t.icon}</span>
          <span class="type-label" style={t.id === currentType ? `color:${t.color}` : ''}>{t.label}</span>
          <span class="type-sub">{t.sub}</span>
        </button>
      {/each}
    </div>
  </div>
</div>

<style>
@keyframes overlay-fade { from { opacity:0 } to { opacity:1 } }
@keyframes modal-in { from { opacity:0;transform:scale(0.95) translateY(-8px) } to { opacity:1;transform:scale(1) translateY(0) } }
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.65); z-index: 300;
  display: flex; align-items: center; justify-content: center;
  animation: overlay-fade 0.15s ease;
}
.modal {
  background: #0d1117; border: 1px solid #21262d; border-radius: 10px; width: 340px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.6);
  animation: modal-in 0.18s cubic-bezier(0.16,1,0.3,1);
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px 10px; border-bottom: 1px solid #21262d;
}
.modal-title { font-size: 13px; font-weight: 700; color: #e6edf3; font-family: 'Figtree', sans-serif; }
.x-btn { background: none; border: none; color: #555; font-size: 14px; cursor: pointer; }
.x-btn:hover { color: #ef4444; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 12px; }
.type-cell {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 14px 8px; border: 1px solid #21262d; border-radius: 8px;
  background: #090d13; cursor: pointer; transition: all 0.15s;
}
.type-cell:hover { background: #21262d; }
.type-icon { font-size: 22px; }
.type-label { font-size: 11px; font-weight: 700; color: #8b949e; font-family: 'Figtree', sans-serif; letter-spacing: 0.06em; }
.type-sub { font-size: 9px; color: #555; font-family: 'Figtree', sans-serif; text-align: center; }
</style>
