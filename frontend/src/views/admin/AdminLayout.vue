<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="admin-shell">
    <RouterView />
  </div>
</template>

<style scoped>
.admin-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 48px;
}
</style>
