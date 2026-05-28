<script setup lang="ts">
defineProps<{ tone?: 'info' | 'success' | 'warning' | 'danger' | 'neutral' }>()
</script>

<template>
  <span class="r-badge" :class="'r-badge-' + (tone || 'neutral')">
    <slot />
  </span>
</template>

<style scoped>
.r-badge { height: var(--r-badge-height); padding: var(--r-badge-padding); border-radius: var(--r-badge-radius); font-size: var(--r-badge-font-size); font-weight: 600; display: inline-flex; align-items: center; white-space: nowrap; }
.r-badge-info    { background: rgba(99, 102, 241, 0.08); color: #6366F1; }
.r-badge-success { background: rgba(16, 185, 129, 0.1); color: #10B981; }
.r-badge-warning { background: rgba(245, 158, 11, 0.1); color: #D97706; }
.r-badge-danger  { background: rgba(239, 68, 68, 0.08); color: #EF4444; }
.r-badge-neutral { background: rgba(148, 163, 184, 0.08); color: #64748B; }
</style>
