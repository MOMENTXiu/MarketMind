<script setup lang="ts">
import { computed } from 'vue'
import { Sparkles } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import type { RecommendationPayload } from '../../utils/data-processing-charts'
import { buildRecommendationMetricsOption, buildReliabilityOption } from '../../utils/data-processing-charts'
import ReportSectionCard from '../report/ReportSectionCard.vue'
import ReportSectionHeader from '../report/ReportSectionHeader.vue'
import ReportPanel from '../report/ReportPanel.vue'

const props = defineProps<{
  payload?: RecommendationPayload | null
}>()

const metricsOption = computed(() => buildRecommendationMetricsOption(props.payload?.evaluation))
const reliabilityOption = computed(() => buildReliabilityOption(props.payload?.reliability))

const hasEvaluation = computed(() => props.payload?.evaluation && props.payload.evaluation.length > 0)
const hasReliability = computed(() => props.payload?.reliability && Object.keys(props.payload.reliability).length > 0)
const hasAnyData = computed(() => hasEvaluation.value || hasReliability.value)
const bestModel = computed(() => props.payload?.best_model)
const fusionHit = computed(() => props.payload?.fusion_hit)

const strengthLabel = computed(() => {
  const h = fusionHit.value
  if (h === undefined || h === null) return null
  if (h >= 0.1) return '高'
  if (h >= 0.05) return '中'
  return '低'
})

const MODEL_NAMES: Record<string, string> = {
  '热门': '热门商品',
  '类目偏好': '类目偏好',
  '图嵌入': '图嵌入协同过滤',
  'CRITIC-TOPSIS': '多信号融合',
}
const modelName = computed(() => bestModel.value ? (MODEL_NAMES[bestModel.value] || bestModel.value) : null)

const actionText = computed(() => {
  if (!hasAnyData.value) return '当前数据不足以生成稳定的个性化推荐结果。'
  const parts: string[] = []
  if (modelName.value) parts.push(`采用${modelName.value}模型`)
  if (strengthLabel.value) parts.push(`推荐强度：${strengthLabel.value}`)
  if (!parts.length) return '推荐系统已就绪。'
  return parts.join('，') + '。可在会员小程序、收银推荐或短信推送中使用推荐结果。'
})
</script>

<template>
  <ReportSectionCard>
    <ReportSectionHeader :icon="Sparkles" title="个性化推荐" description="根据用户行为生成可执行的商品推荐建议" />

    <!-- Business insight card -->
    <div v-if="hasAnyData" class="r-insight r-insight-info">
      <div class="r-insight-title">推荐建议</div>
      <div class="insight-body">
        <div class="insight-row" v-if="modelName">
          <span class="insight-label">推荐策略</span>
          <span>{{ modelName }}模型</span>
        </div>
        <div class="insight-row" v-if="strengthLabel">
          <span class="insight-label">推荐强度</span>
          <span :class="'strength-' + strengthLabel">{{ strengthLabel === '高' ? '高 — 推荐结果较可靠' : strengthLabel === '中' ? '中 — 建议结合业务经验使用' : '低 — 建议积累更多数据后重新分析' }}</span>
        </div>
        <div class="insight-row">
          <span class="insight-label">执行方式</span>
          <span>可在会员小程序首页、收银台提示或短信推送中展示推荐商品</span>
        </div>
        <p class="insight-body-text">{{ actionText }}</p>
      </div>
    </div>
    <div v-else class="r-insight r-insight-muted">
      <p class="insight-empty-text">{{ actionText }}</p>
    </div>

    <!-- Technical charts (foldable) -->
    <details v-if="hasEvaluation || hasReliability" class="tech-details">
      <summary>查看技术指标</summary>
      <div class="rec-charts-grid">
        <ReportPanel v-if="hasEvaluation">
          <h4 class="chart-title">模型指标对比</h4>
          <v-chart :option="metricsOption" autoresize class="dp-chart" />
        </ReportPanel>
        <ReportPanel v-if="hasReliability">
          <h4 class="chart-title">信号可靠性</h4>
          <v-chart :option="reliabilityOption" autoresize class="dp-chart" />
        </ReportPanel>
      </div>
    </details>
  </ReportSectionCard>
</template>

<style scoped>
.rec-charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.dp-chart { height: var(--r-chart-height); width: 100%; }

.r-insight-title { font-size: 0.85rem; font-weight: 800; color: var(--text-primary); margin-bottom: 12px; }
.insight-body { display: flex; flex-direction: column; gap: 8px; }
.insight-row { display: flex; gap: 12px; font-size: 0.85rem; color: var(--text-secondary); }
.insight-label { font-weight: 700; color: var(--text-primary); min-width: 80px; flex-shrink: 0; }
.insight-body-text { font-size: 0.82rem; color: var(--text-tertiary); margin: 4px 0 0 0; line-height: 1.5; }
.insight-empty-text { color: var(--text-tertiary); font-size: 0.85rem; margin: 0; }
.strength-高 { color: #10B981; font-weight: 600; }
.strength-中 { color: #F59E0B; font-weight: 600; }
.strength-低 { color: #EF4444; font-weight: 600; }

.tech-details { margin-top: 8px; }
.tech-details summary { cursor: pointer; font-size: 0.78rem; color: var(--text-tertiary); padding: 8px 0; user-select: none; }
.tech-details .rec-charts-grid { margin-top: 12px; }

@media (max-width: 980px) { .rec-charts-grid { grid-template-columns: 1fr; } }
</style>
