<script>
  import { onMount } from 'svelte';

  /**
   * @type {{
   *   color?: string,
   *   currentIcon?: string,
   *   onSelect?: (icon: string) => void,
   *   onClose?: () => void,
   * }}
   */
  let { color = '#888', currentIcon = '', onSelect, onClose } = $props();

  /** @type {{ brand: Array<{id:string,label:string,color:string,src:string}>, audio: Array<{id:string,label:string,color:string,src:string}> }} */
  let manifest = $state({ brand: [], audio: [] });

  let urlInput = $state('');
  /** @type {HTMLInputElement | null} */
  let fileInput = $state(null);

  onMount(async () => {
    try {
      const res = await fetch('/icons/manifest.json');
      manifest = await res.json();
    } catch { /* manifest not available */ }
  });

  /** @param {string} id */
  function pick(id) { onSelect?.(id); onClose?.(); }

  function pickUrl() {
    if (urlInput.trim()) { onSelect?.(urlInput.trim()); onClose?.(); }
  }

  /** @param {Event} e */
  function handleFileChange(e) {
    const file = /** @type {HTMLInputElement} */ (e.currentTarget).files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => { onSelect?.(/** @type {string} */ (reader.result)); onClose?.(); };
    reader.readAsDataURL(file);
  }
</script>

<div class="overlay" onclick={e => { if (e.target === e.currentTarget) onClose?.(); }}>
  <div class="modal">
    <div class="modal-head">
      <span class="modal-title">Choose Icon</span>
      <button class="x-btn" onclick={onClose}>✕</button>
    </div>

    <div class="scroll-area">
      <!-- Brand icons -->
      {#if manifest.brand.length > 0}
        <div class="section-label">Official App Icons</div>
        <div class="brand-grid">
          {#each manifest.brand as icon}
            <button
              class="icon-cell brand-cell"
              class:active={icon.id === currentIcon}
              style="background:{icon.id === currentIcon ? icon.color + '22' : '#0d1117'};border-color:{icon.id === currentIcon ? icon.color + '88' : '#21262d'}"
              onclick={() => pick(icon.id)}
              title={icon.label}
            >
              <div class="brand-img-wrap" style="background:{icon.color}18;border:1px solid {icon.color}33">
                <img src={icon.src} alt={icon.label} width="28" height="28" style="object-fit:contain">
              </div>
              <span class="brand-name" style="color:{icon.color}">{icon.label}</span>
            </button>
          {/each}
        </div>

        <div class="divider"></div>
      {/if}

      <!-- Audio icons -->
      {#if manifest.audio.length > 0}
        <div class="section-label">Audio &amp; Streaming</div>
        <div class="audio-grid">
          {#each manifest.audio as icon}
            <button
              class="icon-cell audio-cell"
              class:active={icon.id === currentIcon}
              style="background:{icon.id === currentIcon ? icon.color + '22' : 'transparent'};border-color:{icon.id === currentIcon ? icon.color + '88' : '#21262d'}"
              onclick={() => pick(icon.id)}
              title={icon.label}
            >
              <div class="audio-img-wrap" style="background:{icon.color}18;border:1px solid {icon.color}33">
                <img src={icon.src} alt={icon.label} width="24" height="24" style="object-fit:contain">
              </div>
              <span class="audio-label" style="color:{icon.color}">{icon.label}</span>
            </button>
          {/each}
        </div>

        <div class="divider"></div>
      {/if}

      <!-- Custom image -->
      <div class="section-label">Custom Image</div>
      <div class="url-row">
        <input
          class="url-input"
          type="text"
          placeholder="Paste image URL…"
          value={urlInput}
          oninput={e => urlInput = e.currentTarget.value}
          onkeydown={e => e.key === 'Enter' && pickUrl()}
        />
        <button class="url-btn" onclick={pickUrl}>Use</button>
      </div>
      <div class="file-row">
        <input
          bind:this={fileInput}
          type="file"
          accept="image/*"
          style="display:none"
          onchange={handleFileChange}
        />
        <button class="browse-btn" onclick={() => fileInput?.click()}>Browse local image…</button>
      </div>
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
  width: 360px;
  max-height: 82vh;
  display: flex; flex-direction: column;
  box-shadow: 0 16px 48px rgba(0,0,0,0.6);
}

.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px 10px;
  border-bottom: 1px solid #21262d;
  flex-shrink: 0;
}

.modal-title {
  font-size: 13px; font-weight: 700; color: #e6edf3;
  font-family: 'Figtree', sans-serif;
}

.x-btn {
  background: none; border: none; color: #555; font-size: 14px; cursor: pointer;
}
.x-btn:hover { color: #ef4444; }

.scroll-area {
  padding: 12px;
  overflow-y: auto;
  flex: 1;
}

.section-label {
  font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
  color: #484f58; display: block; margin-bottom: 8px;
  font-family: 'Figtree', sans-serif;
}

.divider { height: 1px; background: #21262d; margin: 12px 0; }

/* Brand grid — 2 per row, larger cells */
.brand-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
  margin-bottom: 2px;
}

.brand-cell {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px;
  border-radius: 8px; border: 1px solid #21262d;
  cursor: pointer;
  transition: all 0.12s;
  text-align: left;
}
.brand-cell:hover { filter: brightness(1.15); }

.brand-img-wrap {
  width: 40px; height: 40px;
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.brand-name {
  font-size: 11px; font-weight: 700;
  font-family: 'Figtree', sans-serif;
  letter-spacing: 0.03em;
}

/* Audio grid — 4 per row */
.audio-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  margin-bottom: 2px;
}

.audio-cell {
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  padding: 8px 4px;
  border-radius: 8px; border: 1px solid;
  cursor: pointer;
  transition: all 0.12s;
}
.audio-cell:hover { filter: brightness(1.15); }

.audio-img-wrap {
  width: 40px; height: 40px;
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
}

.audio-label {
  font-size: 9px; font-weight: 600;
  font-family: 'Figtree', sans-serif;
  text-align: center;
  line-height: 1.2;
  max-width: 60px;
}

.url-row {
  display: flex; gap: 8px; margin-bottom: 6px;
}

.url-input {
  flex: 1; padding: 6px 8px;
  background: #0d1117; border: 1px solid #30363d;
  border-radius: 5px; color: #e6edf3; font-size: 11px;
  font-family: 'Figtree', sans-serif;
}
.url-input:focus { outline: none; border-color: #388bfd; }

.url-btn {
  padding: 6px 12px;
  background: #21262d; border: 1px solid #30363d;
  border-radius: 5px; color: #8b949e; font-size: 11px; cursor: pointer;
  font-family: 'Figtree', sans-serif;
}
.url-btn:hover { background: #30363d; color: #e6edf3; }

.file-row { }

.browse-btn {
  width: 100%; padding: 7px 12px;
  background: #21262d; border: 1px solid #30363d;
  border-radius: 5px; color: #8b949e; font-size: 11px; cursor: pointer;
  font-family: 'Figtree', sans-serif; text-align: center;
}
.browse-btn:hover { background: #30363d; color: #e6edf3; }
</style>
