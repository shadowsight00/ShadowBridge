<script>
  /**
   * @type {{
   *   currentColor?: string,
   *   onChange?: (c: string) => void,
   *   onClose?: () => void,
   * }}
   */
  let { currentColor = '#888888', onChange, onClose } = $props();

  const SWATCHES = [
    '#ff6b6b','#ff9f43','#ffd32a','#05c46b',
    '#1db954','#22c55e','#3b82f6','#5865f2',
    '#a855f7','#ec4899','#f59e0b','#14b8a6',
    '#ef4444','#8b5cf6','#06b6d4','#94a3b8',
  ];

  let pick = $state(currentColor);

  function confirm() { onChange?.(pick); onClose?.(); }
</script>

<div class="overlay" onclick={e => { if (e.target === e.currentTarget) onClose?.(); }}>
  <div class="modal">
    <div class="modal-head">
      <span class="modal-title">Choose Color</span>
      <button class="x-btn" onclick={onClose}>✕</button>
    </div>

    <div class="body">
      <div class="swatch-grid">
        {#each SWATCHES as s}
          <button
            class="swatch"
            style="background:{s};{pick === s ? 'box-shadow:0 0 0 2px #e6edf3,0 0 0 4px ' + s : ''}"
            onclick={() => { pick = s; }}
          ></button>
        {/each}
      </div>

      <div class="custom-row">
        <span class="label">Custom</span>
        <input
          type="color"
          value={pick}
          oninput={e => pick = e.currentTarget.value}
          class="color-input"
        />
        <span class="hex">{pick}</span>
      </div>

      <div class="preview" style="background:{pick}22;border-color:{pick}55">
        <span style="color:{pick};font-weight:700">Preview</span>
      </div>
    </div>

    <div class="footer">
      <button class="cancel-btn" onclick={onClose}>Cancel</button>
      <button class="ok-btn" style="background:{pick}" onclick={confirm}>Apply</button>
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
.body { padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; }
.swatch-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 6px;
}
.swatch {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  transition: transform 0.1s;
}
.swatch:hover { transform: scale(1.15); }
.custom-row {
  display: flex; align-items: center; gap: 8px;
}
.label { font-size: 11px; color: #8b949e; font-family: 'Figtree', sans-serif; flex-shrink: 0; }
.color-input { width: 36px; height: 28px; border: 1px solid #30363d; border-radius: 4px; background: none; cursor: pointer; padding: 2px; }
.hex { font-size: 11px; color: #8b949e; font-family: monospace; }
.preview {
  border: 1px solid;
  border-radius: 6px;
  padding: 8px 12px;
  text-align: center;
  font-size: 12px;
  font-family: 'Figtree', sans-serif;
}
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
.ok-btn {
  padding: 5px 16px;
  border: none; border-radius: 5px;
  color: #fff; font-size: 11px; font-weight: 700; cursor: pointer;
  font-family: 'Figtree', sans-serif;
  filter: brightness(0.9);
}
.ok-btn:hover { filter: brightness(1.1); }
</style>
