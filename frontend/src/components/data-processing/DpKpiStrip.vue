<script setup lang="ts">
import { computed } from 'vue'
import { TrendCharts } from '@element-plus/icons-vue'
import type { SummaryPayload } from '../../utils/data-processing-charts'
import { buildKpiTiles } from '../../utils/data-processing-charts'

const props = defineProps<{
  summary?: SummaryPayload | null
}>()

const tiles = computed(() => buildKpiTiles(props.summary))
const hasAnySkipped = computed(() => {
  if (!props.summary) return false
  const modules = ['基础销售统计', '顾客画像', '关联规则', '个性化推荐', '促销分析'] as const
  return modules.some(m => !props.summary?.[m] || Object.keys(props.summary[m] || {}).length === 0)
})
</script>

<template>
  <section class="section-block kpi-section">
    <div class="section-header-modern compact">
      <div class="title-with-icon">
        <el-icon class="icon-main"><TrendCharts /></el-icon>
        <div>
          <h3>分析概览</h3>
          <p>核心指标总览</p>
        </div>
      </div>
    </div>

    <div v-if="tiles.length" class="kpi-grid">
      <div v-for="tile in tiles" :key="tile.label" class="kpi-tile">
        <span class="kpi-label">{{ tile.label }}</span>
        <span class="kpi-value">{{ tile.value }}</span>
        <span v-if="tile.sub" class="kpi-sub">{{ tile.sub }}</span>
      </div>
    </div>
    <el-empty v-else description="暂无概览数据" :image-size="56" />

    <div v-if="hasAnySkipped" class="skipped-hint">
      <span>部分模块因数据条件不足已跳过</span>
    </div>
  </section>
</template>

<style scoped>
.kpi-section { padding: 24px 32px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 16px; }
.kpi-tile { background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 16px; display: flex; flex-direction: column; gap: 6px; }
.kpi-label { font-size: 0.72rem; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-value { font-size: 1.3rem; font-weight: 800; color: var(--text-primary); }
.kpi-sub { font-size: 0.72rem; color: var(--text-tertiary); }
.skipped-hint { margin-top: 12px; font-size: 0.75rem; color: #94a3b8; }
</style>
