<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="admin-shell">
    <RouterView v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </RouterView>
  </div>
</template>

<style scoped>
.admin-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 48px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
