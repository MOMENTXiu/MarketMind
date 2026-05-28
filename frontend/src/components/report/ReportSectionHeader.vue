<script setup lang="ts">
defineProps<{ icon?: any; title: string; description?: string }>()
</script>

<template>
  <div class="r-header">
    <div v-if="icon" class="r-header-icon">
      <component :is="icon" />
    </div>
    <div class="r-header-text">
      <h2 class="r-header-title">{{ title }}</h2>
      <p v-if="description" class="r-header-desc">{{ description }}</p>
    </div>
    <div v-if="$slots.default" class="r-header-extra">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.r-header {
  display: flex;
  align-items: flex-start;
  gap: var(--r-header-gap);
  margin-bottom: 24px;
}
.r-header-icon {
  flex-shrink: 0;
  width: var(--r-header-icon-size);
  height: var(--r-header-icon-size);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(99, 102, 241, 0.08);
  color: #6366F1;
  font-size: 1rem;
  margin-top: 2px;
}
html.dark .r-header-icon {
  background: rgba(99, 102, 241, 0.15);
}
.r-header-title {
  font-size: var(--r-header-title-size);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.3;
}
.r-header-desc {
  font-size: var(--r-header-desc-size);
  color: var(--text-tertiary);
  margin: 4px 0 0 0;
  line-height: 1.4;
}
.r-header-extra {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  flex-wrap: wrap;
}
</style>
