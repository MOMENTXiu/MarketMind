<script setup lang="ts">
import { computed } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import type { PromotionPayload } from '../../utils/data-processing-charts'
import { buildPromotionEffectOption, buildDiscountLevelsOption } from '../../utils/data-processing-charts'
import ReportSectionCard from '../report/ReportSectionCard.vue'
import ReportSectionHeader from '../report/ReportSectionHeader.vue'
import ReportPanel from '../report/ReportPanel.vue'
import ReportBadge from '../report/ReportBadge.vue'

const props = defineProps<{
  payload?: PromotionPayload | null
}>()

const effectOption = computed(() => buildPromotionEffectOption(props.payload))
const discountOption = computed(() => buildDiscountLevelsOption(props.payload?.discount_levels))

const hasEffect = computed(() =>
  props.payload?.naive_diff !== undefined || props.payload?.dml_ate !== undefined
)
const hasDiscount = computed(() => props.payload?.discount_levels && props.payload.discount_levels.length > 0)
const hasAnyData = computed(() => hasEffect.value || hasDiscount.value)
const dmlSignificant = computed(() => props.payload?.dml_significant)
const dmlAte = computed(() => props.payload?.dml_ate)
const naiveDiff = computed(() => props.payload?.naive_diff)
const profitMargin = computed(() => props.payload?.profit_margin)
const totalProfit = computed(() => props.payload?.total_profit)

const effectLabel = computed((): '有效' | '可能有效' | '不明显' | '数据不足' => {
  if (!hasEffect.value) return '数据不足'
  const ate = dmlAte.value ?? 0
  const sig = dmlSignificant.value
  if (sig === true && ate > 0) return '有效'
  if (sig === true && ate <= 0) return '不明显'
  if (sig === false) return '不明显'
  return '数据不足'
})

const conclusionLines = computed((): string[] => {
  if (!hasEffect.value) return ['促销数据不足以生成稳定结论。建议增加样本量或延长观察周期。']
  const ate = dmlAte.value ?? 0
  const sig = dmlSignificant.value
  if (sig === true && ate > 0) {
    return [
      '促销可能带来额外销售增长，参与促销的用户平均消费高于未参与用户。',
      '建议在相似商品或用户群中小范围复用，并持续跟踪效果变化。',
    ]
  }
  if (sig === true && ate <= 0) {
    return [
      '促销未观察到正向收益，促销组表现未优于对照组，可能存在折扣侵蚀利润或选品不匹配。',
      '建议暂停扩大投放，复查促销商品选择和目标用户群。',
    ]
  }
  if (sig === false) {
    return [
      '当前数据尚不能证明促销带来了稳定变化，促销组与对照组差异可能来自自然波动。',
      '建议延长观察周期或增加促销参与样本后再评估。',
    ]
  }
  return ['暂无足够数据进行促销效果判断。']
})

const riskNotes = computed((): string[] => {
  const notes: string[] = []
  if (dmlSignificant.value === false) notes.push('统计显著性不足，结论存在不确定性')
  if (hasEffect.value && Math.abs(naiveDiff.value ?? 0) > Math.abs(dmlAte.value ?? 0) * 3) {
    notes.push('简单对比与因果估计差异较大，可能存在混淆因素（如促销天然面向高消费用户）')
  }
  return notes
})
</script>

<template>
  <ReportSectionCard>
    <ReportSectionHeader :icon="Promotion" title="促销分析" description="评估促销是否带来额外销售增长" />

    <!-- Business conclusion card -->
    <div v-if="hasAnyData" class="r-insight" :class="'r-insight-' + (effectLabel === '有效' ? 'success' : effectLabel === '不明显' ? 'warning' : 'info')">
      <div class="r-insight-title">促销结论</div>
      <div class="effect-badge" :class="'effect-' + effectLabel">{{ effectLabel === '有效' ? '有效 — 促销带来正向收益' : effectLabel === '可能有效' ? '可能有效 — 建议小范围验证' : effectLabel === '不明显' ? '效果不明显 — 需进一步观察' : '数据不足' }}</div>
      <div class="insight-body">
        <div v-for="(line, idx) in conclusionLines" :key="idx" class="conclusion-line">{{ line }}</div>
      </div>
      <div v-if="riskNotes.length" class="risk-notes">
        <div v-for="(note, idx) in riskNotes" :key="idx" class="risk-note">{{ note }}</div>
      </div>
    </div>
    <div v-else class="r-insight r-insight-muted">
      <p class="insight-empty-text">促销数据不足以生成稳定的效果判断。请确保数据包含促销标记字段。</p>
    </div>

    <!-- Technical details (foldable) -->
    <details v-if="hasEffect || hasDiscount" class="tech-details">
      <summary>查看技术指标</summary>
      <div class="promo-meta-inner">
        <ReportBadge v-if="dmlSignificant !== undefined" :tone="dmlSignificant ? 'success' : 'warning'">统计显著性: {{ dmlSignificant ? '显著' : '不显著' }}</ReportBadge>
        <ReportBadge v-if="dmlAte !== undefined" tone="neutral">DML ATE: {{ dmlAte >= 0 ? '+' : '' }}{{ dmlAte.toFixed(2) }}</ReportBadge>
        <ReportBadge v-if="naiveDiff !== undefined" tone="neutral">简单对比: {{ naiveDiff >= 0 ? '+' : '' }}{{ naiveDiff.toFixed(2) }}</ReportBadge>
        <ReportBadge v-if="profitMargin !== undefined" tone="neutral">利润率: {{ (profitMargin * 100).toFixed(1) }}%</ReportBadge>
        <ReportBadge v-if="totalProfit !== undefined" tone="neutral">总利润: ¥{{ totalProfit.toLocaleString('zh-CN') }}</ReportBadge>
      </div>
      <div class="promo-charts-grid">
        <ReportPanel v-if="hasEffect">
          <h4 class="chart-title">因果效应对比</h4>
          <v-chart :option="effectOption" autoresize class="dp-chart" />
        </ReportPanel>
        <ReportPanel v-if="hasDiscount">
          <h4 class="chart-title">折扣档位响应</h4>
          <v-chart :option="discountOption" autoresize class="dp-chart" />
        </ReportPanel>
      </div>
    </details>
  </ReportSectionCard>
</template>

<style scoped>
.promo-charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.dp-chart { height: var(--r-chart-height); width: 100%; }

.r-insight-title { font-size: 0.85rem; font-weight: 800; color: var(--text-primary); margin-bottom: 12px; }
.effect-badge { display: inline-block; font-size: 0.8rem; font-weight: 700; padding: 4px 12px; border-radius: 999px; margin-bottom: 12px; }
.effect-有效 { background: rgba(16, 185, 129, 0.12); color: #10B981; }
.effect-可能有效 { background: rgba(245, 158, 11, 0.12); color: #D97706; }
.effect-不明显 { background: rgba(239, 68, 68, 0.1); color: #DC2626; }
.effect-数据不足 { background: rgba(148, 163, 184, 0.1); color: #64748B; }
.insight-body { display: flex; flex-direction: column; gap: 6px; }
.conclusion-line { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; }
.insight-empty-text { color: var(--text-tertiary); font-size: 0.85rem; margin: 0; }
.risk-notes { margin-top: 12px; display: flex; flex-direction: column; gap: 4px; }
.risk-note { font-size: 0.75rem; color: #D97706; }
.risk-note::before { content: '⚠ '; }

.promo-meta-inner { display: flex; gap: 6px; flex-wrap: wrap; margin: 12px 0 16px; }

.tech-details { margin-top: 8px; }
.tech-details summary { cursor: pointer; font-size: 0.78rem; color: var(--text-tertiary); padding: 8px 0; user-select: none; }

@media (max-width: 980px) { .promo-charts-grid { grid-template-columns: 1fr; } }
</style>
