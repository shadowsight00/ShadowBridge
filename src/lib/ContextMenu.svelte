<script>
  /**
   * @type {{
   *   x: number,
   *   y: number,
   *   channelEnabled: boolean,
   *   onAction: (action: string) => void,
   *   onClose: () => void,
   * }}
   */
  let { x, y, channelEnabled, onAction, onClose } = $props();

  /** @param {string} action */
  function act(action) { onAction(action); onClose(); }

  /** @param {MouseEvent} e */
  function backdropClick(e) { if (e.target === e.currentTarget) onClose(); }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="backdrop" onmousedown={backdropClick} oncontextmenu={e => { e.preventDefault(); onClose(); }}>
  <div class="menu" style="left:{x}px;top:{y}px">
    <button class="item" onclick={() => act('rename')}>Rename Channel</button>
    <button class="item" onclick={() => act('device')}>Select Source</button>
    <button class="item" onclick={() => act('type')}>Change Direction</button>
    <button class="item" onclick={() => act('color')}>Change Color</button>
    <button class="item" onclick={() => act('icon')}>Change Icon</button>
    <div class="sep"></div>
    <button class="item" onclick={() => act('toggle')}>{channelEnabled ? 'Turn Off' : 'Turn On'}</button>
    <button class="item" onclick={() => act('info')}>Channel Info</button>
    <div class="sep"></div>
    <button class="item danger" onclick={() => act('delete')}>Delete Channel</button>
  </div>
</div>

<style>
.backdrop {
  position: fixed; inset: 0;
  z-index: 400;
}
.menu {
  position: fixed;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.7);
  padding: 4px;
  min-width: 170px;
  animation: menu-in 0.1s ease;
  z-index: 401;
}
@keyframes menu-in { from { opacity:0; transform:scale(0.96) translateY(-4px); } to { opacity:1; transform:scale(1) translateY(0); } }
.item {
  display: block; width: 100%;
  padding: 6px 12px;
  background: none; border: none;
  color: #c9d1d9; font-size: 12px;
  font-family: 'Figtree', sans-serif;
  text-align: left; cursor: pointer;
  border-radius: 5px;
  transition: background 0.1s;
}
.item:hover { background: #21262d; color: #e6edf3; }
.item.danger { color: #f85149; }
.item.danger:hover { background: #2d1018; }
.sep {
  height: 1px; background: #21262d;
  margin: 4px 0;
}
</style>
