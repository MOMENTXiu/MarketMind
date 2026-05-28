<script setup lang="ts">
import { computed } from 'vue'
import { Star } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import type { RecommendationPayload } from '../../utils/data-processing-charts'
import { buildRecommendationMetricsOption, buildReliabilityOption } from '../../utils/data-processing-charts'

const props = defineProps<{
  payload?: RecommendationPayload | null
}>()

const metricsOption = computed(() => buildRecommendationMetricsOption(props.payload?.evaluation))
const reliabilityOption = computed(() => buildReliabilityOption(props.payload?.reliability))

const hasEvaluation = computed(() => props.payload?.evaluation && props.payload.evaluation.length > 0)
const hasReliability = computed(() => props.payload?.reliability && Object.keys(props.payload.reliability).length > 0)
const bestModel = computed(() => props.payload?.best_model)
const fusionHit = computed(() => props.payload?.fusion_hit)
</script>

<template>
  <section class="section-block">
    <div class="section-header-modern compact">
      <div class="title-with-icon">
        <el-icon class="icon-main"><Star /></el-icon>
        <div>
          <h3>个性化推荐</h3>
          <p>模型评估与信号可靠性</p>
        </div>
      </div>
      <div v-if="bestModel || fusionHit !== undefined" class="rec-meta">
        <span v-if="bestModel" class="meta-tag">最佳: {{ bestModel }}</span>
        <span v-if="fusionHit !== undefined" class="meta-tag">融合命中率: {{ (fusionHit * 100).toFixed(1) }}%</span>
      </div>
    </div>

    <div class="rec-charts-grid">
      <div v-if="hasEvaluation" class="chart-card">
        <h4 class="chart-title">模型指标对比</h4>
        <v-chart :option="metricsOption" autoresize class="dp-chart" />
      </div>
      <div v-else class="chart-card empty">
        <el-empty description="暂无模型评估" :image-size="56" />
      </div>

      <div v-if="hasReliability" class="chart-card">
        <h4 class="chart-title">信号可靠性</h4>
        <v-chart :option="reliabilityOption" autoresize class="dp-chart" />
      </div>
      <div v-else class="chart-card empty">
        <el-empty description="暂无可靠性数据" :image-size="56" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.rec-charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.chart-card { background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 20px; padding: 16px; }
.chart-card.empty { display: flex; align-items: center; justify-content: center; min-height: 280px; }
.chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.dp-chart { height: 280px; width: 100%; }
.rec-meta { display: flex; gap: 8px; }
.meta-tag { font-size: 0.72rem; padding: 4px 10px; background: var(--color-accent-soft); color: var(--color-accent); border-radius: 999px; font-weight: 700; }
@media (max-width: 980px) { .rec-charts-grid { grid-template-columns: 1fr; } }
</style>
