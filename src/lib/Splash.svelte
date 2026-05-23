<script>
  import { onMount } from 'svelte';

  /** @type {{ done: () => void }} */
  let { done } = $props();

  onMount(() => {
    const timer = setTimeout(() => done(), 2800);
    return () => clearTimeout(timer);
  });
</script>

<div class="splash" onanimationend={(e) => e.animationName === 'fadeOut' && done()}>
  <img src="/assets/splash_logo.png" alt="ShadowBridge" class="logo" />
  <div class="bar-wrap">
    <div class="bar"></div>
  </div>
</div>

<style>
  .splash {
    position: fixed;
    inset: 0;
    background: #000;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 40px;
    z-index: 9999;
    animation: fadeOut 0.6s ease-in-out 2.3s forwards;
  }

  .logo {
    width: 480px;
    max-width: 80vw;
    animation: fadeIn 0.8s ease-out forwards;
    opacity: 0;
  }

  .bar-wrap {
    width: 220px;
    height: 2px;
    background: #1e2a35;
    border-radius: 2px;
    overflow: hidden;
  }

  .bar {
    height: 100%;
    background: linear-gradient(90deg, #1e3a5f, #58a6ff, #1e3a5f);
    border-radius: 2px;
    animation: load 2.0s ease-in-out 0.3s forwards;
    width: 0%;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: scale(0.96); }
    to   { opacity: 1; transform: scale(1); }
  }

  @keyframes load {
    from { width: 0%; }
    to   { width: 100%; }
  }

  @keyframes fadeOut {
    from { opacity: 1; }
    to   { opacity: 0; pointer-events: none; }
  }
</style>
