<script>
  /** @type {{ level?: number, color?: string }} */
  let { level = 0, color = '#22c55e' } = $props();

  // Enough bars to extend well beyond the tallest expected strip.
  // Each bar is 5px + 1.5px gap = 6.5px → 60 bars ≈ 390px.
  const NUM = 60;
  const DIM = '#21262d';

  // Lit bars count from the bottom (index 0 = bottom visual with column-reverse).
  const numActive = $derived(Math.round(Math.max(0, Math.min(1, level)) * NUM));

  /**
   * i=0 is the bottom-most bar (low signal), i=NUM-1 is the top (clip).
   * @param {number} i
   */
  function segColor(i) {
    if (i >= NUM - 2) return '#ef4444';
    if (i >= NUM - 4) return '#eab308';
    return color;
  }
</script>

<!--
  column-reverse: first DOM element (i=0) renders at the visual bottom.
  overflow:hidden clips the top — so bars always extend from the bottom up,
  and the visible count grows naturally as the container gets taller.
-->
<div class="meter">
  {#each Array(NUM) as _, i}
    <div class="seg" style="background:{i < numActive ? segColor(i) : DIM}"></div>
  {/each}
</div>

<style>
.meter {
  display: flex;
  flex-direction: column-reverse;
  gap: 1.5px;
  width: 9px;
  align-self: stretch; /* fill whatever height the parent gives us */
  flex-shrink: 0;
  overflow: hidden;   /* clip bars that don't fit at the top */
}
.seg {
  width: 9px;
  height: 5px;
  border-radius: 1px;
  flex-shrink: 0;     /* never squash — bars always stay 5px tall */
  transition: background 40ms linear;
}
</style>
