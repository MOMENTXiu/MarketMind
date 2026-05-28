<script setup lang="ts">
import { computed } from 'vue'
import { ShoppingCart } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import type { AssociationPayload } from '../../utils/data-processing-charts'
import { buildAssociationBubbleOption, buildHuimBarOption } from '../../utils/data-processing-charts'
import ReportSectionCard from '../report/ReportSectionCard.vue'
import ReportSectionHeader from '../report/ReportSectionHeader.vue'
import ReportPanel from '../report/ReportPanel.vue'
import ReportBadge from '../report/ReportBadge.vue'

const props = defineProps<{
  payload?: AssociationPayload | null
}>()

const bubbleResult = computed(() => buildAssociationBubbleOption(props.payload?.rules))
const bubbleOption = computed(() => bubbleResult.value.option)
const bubbleLegend = computed(() => bubbleResult.value.legendItems)
const huimOption = computed(() => buildHuimBarOption(props.payload?.huim))

const hasRules = computed(() => props.payload?.rules && props.payload.rules.length > 0)
const hasHuim = computed(() => props.payload?.huim && props.payload.huim.length > 0)
const nRules = computed(() => props.payload?.n_rules)
const avgLift = computed(() => props.payload?.avg_lift)

const topRules = computed(() => {
  if (!props.payload?.rules?.length) return []
  return props.payload.rules
    .slice()
    .sort((a, b) => (b.提升度 ?? 0) - (a.提升度 ?? 0))
    .slice(0, 5)
    .map(rule => ({
      ant: String(rule.前项 ?? ''),
      con: String(rule.后项 ?? ''),
      conf: Number(rule.置信度 ?? 0),
      lift: Number(rule.提升度 ?? 0),
      explain: `购买「${rule.前项}」的顾客，更容易继续购买「${rule.后项}」。可用于商品陈列、捆绑销售或收银推荐。`,
    }))
})
</script>

<template>
  <ReportSectionCard>
    <ReportSectionHeader :icon="ShoppingCart" title="关联分析" description="发现常被一起购买的商品组合，用于陈列和捆绑销售">
      <template v-if="nRules !== undefined || avgLift !== undefined">
        <ReportBadge v-if="nRules !== undefined" tone="info">规则数: {{ nRules }}</ReportBadge>
        <ReportBadge v-if="avgLift !== undefined" tone="info">平均提升度: {{ avgLift.toFixed(2) }}</ReportBadge>
      </template>
    </ReportSectionHeader>

    <div class="assoc-charts-grid">
      <ReportPanel v-if="hasRules">
        <h4 class="chart-title">置信度-提升度-支持度</h4>
        <v-chart :option="bubbleOption" autoresize class="dp-chart" />
        <div v-if="bubbleLegend.length" class="custom-legend">
          <div v-for="item in bubbleLegend" :key="item.name" class="legend-chip">
            <span class="legend-dot" :style="{ backgroundColor: item.color }"></span>
            <span class="legend-name">{{ item.name }}</span>
          </div>
        </div>
      </ReportPanel>
      <ReportPanel v-else class="chart-empty">
        <el-empty description="暂无关联规则" :image-size="56" />
      </ReportPanel>

      <ReportPanel v-if="hasHuim">
        <h4 class="chart-title">Top 组合效用</h4>
        <v-chart :option="huimOption" autoresize class="dp-chart" />
      </ReportPanel>
      <ReportPanel v-else class="chart-empty">
        <el-empty description="暂无组合效用数据" :image-size="56" />
      </ReportPanel>
    </div>

    <div v-if="topRules.length" class="rules-preview">
      <h4 class="preview-title">Top 规则预览</h4>
      <div class="rules-table">
        <div v-for="(rule, idx) in topRules" :key="idx" class="rule-row">
          <div class="rule-main">
            <span class="rule-ant">{{ rule.ant }}</span>
            <span class="rule-arrow">→</span>
            <span class="rule-con">{{ rule.con }}</span>
            <span class="rule-metrics">
              置信度 {{ (rule.conf * 100).toFixed(1) }}% ·
              提升度 {{ rule.lift.toFixed(2) }}
            </span>
          </div>
          <div class="rule-explain">{{ rule.explain }}</div>
        </div>
      </div>
    </div>
  </ReportSectionCard>
</template>

<style scoped>
.assoc-charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.chart-empty { display: flex; align-items: center; justify-content: center; min-height: var(--r-chart-height); }
.dp-chart { height: var(--r-chart-height); width: 100%; }
.rules-preview { margin-top: 20px; }
.preview-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.rules-table { display: flex; flex-direction: column; gap: 8px; }
.rule-row { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; background: var(--r-panel-bg); border: var(--r-panel-border); border-radius: var(--r-panel-radius); font-size: 0.82rem; }
.rule-main { display: flex; align-items: center; gap: 12px; }
.rule-ant { color: var(--text-primary); font-weight: 600; }
.rule-arrow { color: var(--color-accent); font-weight: 700; }
.rule-con { color: var(--color-accent); font-weight: 700; }
.rule-metrics { margin-left: auto; color: var(--text-tertiary); font-size: 0.75rem; white-space: nowrap; }
.rule-explain { font-size: 0.72rem; color: var(--text-tertiary); line-height: 1.4; }
.custom-legend { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px 14px; margin-top: 10px; }
.legend-chip { display: flex; align-items: center; gap: 5px; font-size: 0.72rem; color: var(--text-secondary); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.legend-name { white-space: nowrap; }
@media (max-width: 980px) { .assoc-charts-grid { grid-template-columns: 1fr; } }
</style>
