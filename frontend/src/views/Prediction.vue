<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="page-container">
    <el-page-header @back="router.back()" title="返回">
      <template #content>
        <span class="page-title">📈 销售预测</span>
      </template>
    </el-page-header>
    <div class="content">
      <el-alert title="功能开发中" type="info" description="销售预测功能正在开发中..." :closable="false" show-icon />
    </div>
  </div>
</template>

<style scoped>
.page-container { padding: 2rem; max-width: 1400px; margin: 0 auto; }
.page-title { font-size: 1.5rem; font-weight: bold; }
.content { margin-top: 2rem; }
</style>
