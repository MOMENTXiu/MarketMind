<template>
  <section class="r-section">
    <slot />
  </section>
</template>

<style scoped>
.r-section {
  background: var(--r-section-bg);
  border: var(--r-section-border);
  border-radius: var(--r-section-radius);
  padding: var(--r-section-padding);
  box-shadow: var(--r-section-shadow);
  margin-bottom: var(--r-section-gap);
}
html.dark .r-section {
  background: var(--color-surface, #1a1a2e);
  border-color: rgba(255, 255, 255, 0.06);
}
</style>
