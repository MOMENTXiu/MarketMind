<script setup lang="ts">
import { computed } from 'vue'
import { User } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import type { SegmentPayload } from '../../utils/data-processing-charts'
import { buildSegmentContributionOption, buildSegmentRadarOption, buildKScanOption } from '../../utils/data-processing-charts'

const props = defineProps<{
  payload?: SegmentPayload | null
}>()

const contributionOption = computed(() => buildSegmentContributionOption(props.payload?.segment_profiles))
const radarOption = computed(() => buildSegmentRadarOption(props.payload?.segment_profiles))
const kscanOption = computed(() => buildKScanOption(props.payload?.kscan))

const hasProfiles = computed(() => props.payload?.segment_profiles && props.payload.segment_profiles.length > 0)
const hasKscan = computed(() => props.payload?.kscan && props.payload.kscan.length > 0)
const silhouette = computed(() => props.payload?.silhouette)
const nSegments = computed(() => props.payload?.n_segments)
const radarKey = computed(() => `radar-${props.payload?.segment_profiles?.length ?? 0}-${props.payload?.silhouette ?? 0}`)
</script>

<template>
  <section class="section-block">
    <div class="section-header-modern compact">
      <div class="title-with-icon">
        <el-icon class="icon-main"><User /></el-icon>
        <div>
          <h3>客户分群</h3>
          <p>识别不同类型客户，用于会员运营和精准推荐</p>
        </div>
      </div>
      <div v-if="nSegments !== undefined || silhouette !== undefined" class="segment-meta">
        <span v-if="nSegments !== undefined" class="meta-tag">K={{ nSegments }}</span>
        <span v-if="silhouette !== undefined" class="meta-tag">轮廓系数={{ silhouette.toFixed(3) }}</span>
      </div>
    </div>

    <div class="segment-charts-grid">
      <div v-if="hasProfiles" class="chart-card">
        <h4 class="chart-title">人数 vs 销售贡献</h4>
        <v-chart :option="contributionOption" autoresize class="dp-chart" />
      </div>
      <div v-else class="chart-card empty">
        <el-empty description="暂无分群画像" :image-size="56" />
      </div>

      <div v-if="hasProfiles" class="chart-card">
        <h4 class="chart-title">分群雷达图</h4>
        <v-chart :key="radarKey" :option="radarOption" autoresize class="dp-chart" />
      </div>
      <div v-else class="chart-card empty">
        <el-empty description="暂无雷达数据" :image-size="56" />
      </div>

      <div v-if="hasKscan" class="chart-card wide">
        <h4 class="chart-title">K-Scan 模型选择</h4>
        <v-chart :option="kscanOption" autoresize class="dp-chart" />
      </div>
      <div v-else class="chart-card wide empty">
        <el-empty description="暂无 K-Scan 数据" :image-size="56" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.segment-charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.segment-charts-grid .wide { grid-column: 1 / -1; }
.chart-card { background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 20px; padding: 16px; }
.chart-card.empty { display: flex; align-items: center; justify-content: center; min-height: 280px; }
.chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.dp-chart { height: 280px; width: 100%; }
.segment-meta { display: flex; gap: 8px; }
.meta-tag { font-size: 0.72rem; padding: 4px 10px; background: var(--color-accent-soft); color: var(--color-accent); border-radius: 999px; font-weight: 700; }
@media (max-width: 980px) { .segment-charts-grid { grid-template-columns: 1fr; } }
</style>
