<script setup lang="ts">
import { computed } from 'vue'
import { DataLine } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import type { OverviewPayload } from '../../utils/data-processing-charts'
import { buildCategoryParetoOption, buildDailySalesTrendOption } from '../../utils/data-processing-charts'

const props = defineProps<{
  payload?: OverviewPayload | null
}>()

const paretoOption = computed(() => buildCategoryParetoOption(props.payload?.category_sales))
const trendOption = computed(() => buildDailySalesTrendOption(props.payload?.daily_sales))
const hasPareto = computed(() => props.payload?.category_sales && props.payload.category_sales.length > 0)
const hasTrend = computed(() => props.payload?.daily_sales && props.payload.daily_sales.length > 0)
</script>

<template>
  <section class="section-block">
    <div class="section-header-modern compact">
      <div class="title-with-icon">
        <el-icon class="icon-main"><DataLine /></el-icon>
        <div>
          <h3>销售概览</h3>
          <p>销售额趋势与品类贡献分析</p>
        </div>
      </div>
    </div>

    <div class="overview-charts-grid">
      <div v-if="hasPareto" class="chart-card">
        <h4 class="chart-title">类目帕累托</h4>
        <v-chart :option="paretoOption" autoresize class="dp-chart" />
      </div>
      <div v-else class="chart-card empty">
        <el-empty description="暂无类目数据" :image-size="56" />
      </div>

      <div v-if="hasTrend" class="chart-card">
        <h4 class="chart-title">日销售趋势</h4>
        <v-chart :option="trendOption" autoresize class="dp-chart" />
      </div>
      <div v-else class="chart-card empty">
        <el-empty description="暂无趋势数据" :image-size="56" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.overview-charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.chart-card { background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 20px; padding: 16px; }
.chart-card.empty { display: flex; align-items: center; justify-content: center; min-height: 280px; }
.chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.dp-chart { height: 280px; width: 100%; }
@media (max-width: 980px) { .overview-charts-grid { grid-template-columns: 1fr; } }
</style>
