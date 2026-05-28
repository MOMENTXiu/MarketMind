<template>
  <div class="r-panel">
    <slot />
  </div>
</template>

<style scoped>
.r-panel {
  background: var(--r-panel-bg);
  border: var(--r-panel-border);
  border-radius: var(--r-panel-radius);
  padding: var(--r-panel-padding);
}
html.dark .r-panel {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.05);
}
</style>
