<script setup lang="ts">
import { computed } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import type { PromotionPayload } from '../../utils/data-processing-charts'
import { buildPromotionEffectOption, buildDiscountLevelsOption } from '../../utils/data-processing-charts'

const props = defineProps<{
  payload?: PromotionPayload | null
}>()

const effectOption = computed(() => buildPromotionEffectOption(props.payload))
const discountOption = computed(() => buildDiscountLevelsOption(props.payload?.discount_levels))

const hasEffect = computed(() =>
  props.payload?.naive_diff !== undefined || props.payload?.dml_ate !== undefined
)
const hasDiscount = computed(() => props.payload?.discount_levels && props.payload.discount_levels.length > 0)
const dmlSignificant = computed(() => props.payload?.dml_significant)
const profitMargin = computed(() => props.payload?.profit_margin)
const totalProfit = computed(() => props.payload?.total_profit)
</script>

<template>
  <section class="section-block">
    <div class="section-header-modern compact">
      <div class="title-with-icon">
        <el-icon class="icon-main"><Promotion /></el-icon>
        <div>
          <h3>促销分析</h3>
          <p>因果效应与折扣响应</p>
        </div>
      </div>
      <div class="promo-meta">
        <span v-if="dmlSignificant !== undefined" class="meta-tag" :class="{ significant: dmlSignificant }">
          DML {{ dmlSignificant ? '显著' : '不显著' }}
        </span>
        <span v-if="profitMargin !== undefined" class="meta-tag">利润率: {{ (profitMargin * 100).toFixed(1) }}%</span>
        <span v-if="totalProfit !== undefined" class="meta-tag">总利润: ¥{{ totalProfit.toLocaleString('zh-CN') }}</span>
      </div>
    </div>

    <div class="promo-charts-grid">
      <div v-if="hasEffect" class="chart-card">
        <h4 class="chart-title">因果效应对比 (Naive vs DML)</h4>
        <v-chart :option="effectOption" autoresize class="dp-chart" />
      </div>
      <div v-else class="chart-card empty">
        <el-empty description="暂无效应数据" :image-size="56" />
      </div>

      <div v-if="hasDiscount" class="chart-card">
        <h4 class="chart-title">折扣档位响应</h4>
        <v-chart :option="discountOption" autoresize class="dp-chart" />
      </div>
      <div v-else class="chart-card empty">
        <el-empty description="暂无折扣数据" :image-size="56" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.promo-charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.chart-card { background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 20px; padding: 16px; }
.chart-card.empty { display: flex; align-items: center; justify-content: center; min-height: 280px; }
.chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.dp-chart { height: 280px; width: 100%; }
.promo-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-tag { font-size: 0.72rem; padding: 4px 10px; background: var(--color-accent-soft); color: var(--color-accent); border-radius: 999px; font-weight: 700; }
.meta-tag.significant { background: rgba(16, 185, 129, 0.15); color: #10B981; }
@media (max-width: 980px) { .promo-charts-grid { grid-template-columns: 1fr; } }
</style>
