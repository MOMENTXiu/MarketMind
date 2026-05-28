<script setup lang="ts">
import { computed } from 'vue'
import { TrendingUp } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import ReportSectionCard from '../report/ReportSectionCard.vue'
import ReportSectionHeader from '../report/ReportSectionHeader.vue'
import ReportPanel from '../report/ReportPanel.vue'
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
  <ReportSectionCard>
    <ReportSectionHeader :icon="TrendingUp" title="销售概览" description="销售额趋势与品类贡献分析" />

    <div class="overview-charts-grid">
      <ReportPanel v-if="hasPareto">
        <h4 class="chart-title">类目帕累托</h4>
        <v-chart :option="paretoOption" autoresize class="dp-chart" />
      </ReportPanel>
      <ReportPanel v-else class="chart-empty">
        <el-empty description="暂无类目数据" :image-size="56" />
      </ReportPanel>

      <ReportPanel v-if="hasTrend">
        <h4 class="chart-title">日销售趋势</h4>
        <v-chart :option="trendOption" autoresize class="dp-chart" />
      </ReportPanel>
      <ReportPanel v-else class="chart-empty">
        <el-empty description="暂无趋势数据" :image-size="56" />
      </ReportPanel>
    </div>
  </ReportSectionCard>
</template>

<style scoped>
.overview-charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.chart-empty { display: flex; align-items: center; justify-content: center; min-height: var(--r-chart-height); }
.dp-chart { height: var(--r-chart-height); width: 100%; }
@media (max-width: 980px) { .overview-charts-grid { grid-template-columns: 1fr; } }
</style>
