<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 直接跳转到项目列表页
onMounted(() => {
  router.replace('/projects')
})
</script>

<template>
  <div class="loading">
    <p>正在跳转...</p>
  </div>
</template>

<style scoped>
.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}
</style>
