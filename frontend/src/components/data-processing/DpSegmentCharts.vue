<script setup lang="ts">
import { computed } from 'vue'
import { Users } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import ReportSectionCard from '../report/ReportSectionCard.vue'
import ReportSectionHeader from '../report/ReportSectionHeader.vue'
import ReportPanel from '../report/ReportPanel.vue'
import ReportBadge from '../report/ReportBadge.vue'
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
  <ReportSectionCard>
    <ReportSectionHeader :icon="Users" title="客户分群" description="识别不同类型客户，用于会员运营和精准推荐">
      <template v-if="nSegments !== undefined || silhouette !== undefined">
        <ReportBadge v-if="nSegments !== undefined" tone="info">K={{ nSegments }}</ReportBadge>
        <ReportBadge v-if="silhouette !== undefined" tone="info">轮廓系数={{ silhouette.toFixed(3) }}</ReportBadge>
      </template>
    </ReportSectionHeader>

    <div class="segment-charts-grid">
      <ReportPanel v-if="hasProfiles">
        <h4 class="chart-title">人数 vs 销售贡献</h4>
        <v-chart :option="contributionOption" autoresize class="dp-chart" />
      </ReportPanel>
      <ReportPanel v-else class="chart-empty">
        <el-empty description="暂无分群画像" :image-size="56" />
      </ReportPanel>

      <ReportPanel v-if="hasProfiles">
        <h4 class="chart-title">分群雷达图</h4>
        <v-chart :key="radarKey" :option="radarOption" autoresize class="dp-chart" />
      </ReportPanel>
      <ReportPanel v-else class="chart-empty">
        <el-empty description="暂无雷达数据" :image-size="56" />
      </ReportPanel>

      <ReportPanel v-if="hasKscan" class="wide">
        <h4 class="chart-title">K-Scan 模型选择</h4>
        <v-chart :option="kscanOption" autoresize class="dp-chart" />
      </ReportPanel>
      <ReportPanel v-else class="chart-empty wide">
        <el-empty description="暂无 K-Scan 数据" :image-size="56" />
      </ReportPanel>
    </div>
  </ReportSectionCard>
</template>

<style scoped>
.segment-charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.segment-charts-grid .wide { grid-column: 1 / -1; }
.chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); margin: 0 0 12px 0; }
.chart-empty { display: flex; align-items: center; justify-content: center; min-height: var(--r-chart-height); }
.dp-chart { height: var(--r-chart-height); width: 100%; }
@media (max-width: 980px) { .segment-charts-grid { grid-template-columns: 1fr; } }
</style>
