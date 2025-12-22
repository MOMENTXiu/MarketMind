<script setup lang="ts">
// 语音播报页面 - 待实现
</script>

<template>
  <div class="page-container">
    <el-page-header @back="$router.back()" title="返回">
      <template #content>
        <span class="page-title">🔊 智能语音播报</span>
      </template>
    </el-page-header>

    <div class="content">
      <el-alert
        title="功能开发中"
        type="info"
        description="语音播报功能正在开发中，将使用AI生成分析报告并进行语音播报..."
        :closable="false"
        show-icon
      />
    </div>
  </div>
</template>

<style scoped>
.page-container {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 1.5rem;
  font-weight: bold;
}

.content {
  margin-top: 2rem;
}
</style>
