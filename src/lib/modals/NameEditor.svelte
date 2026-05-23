<script>
  /**
   * @type {{
   *   currentName?: string,
   *   onSave?: (name: string) => void,
   *   onClose?: () => void,
   * }}
   */
  let { currentName = '', onSave, onClose } = $props();

  let value = $state(currentName);

  function submit() {
    const n = value.trim();
    if (n) { onSave?.(n); onClose?.(); }
  }

  /** @param {KeyboardEvent} e */
  function onKey(e) { if (e.key === 'Enter') submit(); if (e.key === 'Escape') onClose?.(); }
</script>

<div class="overlay" onclick={e => { if (e.target === e.currentTarget) onClose?.(); }}>
  <div class="modal">
    <div class="modal-head">
      <span class="modal-title">Rename Channel</span>
      <button class="x-btn" onclick={onClose}>✕</button>
    </div>
    <div class="body">
      <input
        class="name-input"
        type="text"
        value={value}
        maxlength="16"
        oninput={e => value = e.currentTarget.value}
        onkeydown={onKey}
        placeholder="Channel name…"
        autofocus
      />
      <div class="char-count" class:warn={value.length >= 14}>{value.length}/16</div>
    </div>
    <div class="footer">
      <button class="cancel-btn" onclick={onClose}>Cancel</button>
      <button class="save-btn" onclick={submit}>Save</button>
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
.body { padding: 16px; }
.name-input {
  width: 100%;
  padding: 8px 10px;
  background: #090d13;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #e6edf3;
  font-size: 13px;
  font-family: 'Figtree', sans-serif;
}
.name-input:focus { outline: none; border-color: #388bfd; }
.char-count {
  font-size: 9px; color: #444; font-family: monospace;
  text-align: right; margin-top: 3px;
}
.char-count.warn { color: #f59e0b; }
.footer {
  display: flex; gap: 8px;
  padding: 10px 16px 14px;
  border-top: 1px solid #21262d;
  justify-content: flex-end;
}
.cancel-btn {
  padding: 5px 14px;
  background: #21262d; border: 1px solid #30363d;
  border-radius: 5px; color: #8b949e; font-size: 11px; cursor: pointer;
  font-family: 'Figtree', sans-serif;
}
.cancel-btn:hover { color: #e6edf3; }
.save-btn {
  padding: 5px 16px;
  background: #238636; border: 1px solid #2ea043;
  border-radius: 5px; color: #fff; font-size: 11px; font-weight: 700; cursor: pointer;
  font-family: 'Figtree', sans-serif;
}
.save-btn:hover { background: #2ea043; }
</style>
