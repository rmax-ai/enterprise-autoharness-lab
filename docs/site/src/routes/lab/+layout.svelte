<script>
  import LabSidebar from "$lib/components/layout/LabSidebar.svelte";

  let { children } = $props();
</script>

<section class="lab-shell">
  <aside>
    <LabSidebar />
  </aside>
  <div class="lab-content">
    {@render children()}
  </div>
</section>

<style>
  .lab-shell {
    width: min(1280px, calc(100% - 2rem));
    margin: 0 auto;
    padding: 2rem 0 4rem;
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: 1.5rem;
  }

  .lab-content {
    min-width: 0;
  }

  @media (max-width: 900px) {
    .lab-shell {
      grid-template-columns: 1fr;
      padding-top: 1rem;
    }
  }
</style>
