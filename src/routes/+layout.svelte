<script>
  import Splash from '$lib/Splash.svelte';
  let { children } = $props();
  let showSplash = $state(true);
</script>

{#if showSplash}
  <Splash done={() => { showSplash = false; }} />
{/if}

{@render children()}
