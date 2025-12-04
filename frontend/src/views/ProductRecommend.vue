<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

interface RecommendRule {
  from_items: string[]
  to_items: string[]
  support: number
  confidence: number
  lift: number
  strategy?: string
}

interface RecommendResult {
  item: string
  as_antecedent: RecommendRule[]
  as_consequent: RecommendRule[]
}

const route = useRoute()
const keyword = ref('')
const loading = ref(false)
const result = ref<RecommendResult | null>(null)

const formatPercent = (val: number) => `${(val * 100).toFixed(2)}%`
const formatLift = (val: number) => val.toFixed(2)

const currentProjectId = () => {
  return (route.params.id as string) || ''
}

const search = async () => {
  if (!keyword.value.trim()) {
    ElMessage.warning('请输入商品名称')
    return
  }
  loading.value = true
  try {
    const pid = currentProjectId()
    const response = await axios.get(`/api/projects/${pid || 'default'}/recommend`, {
      params: { item: keyword.value.trim() }
    })
    result.value = response.data
    if (
      (!result.value.as_antecedent || result.value.as_antecedent.length === 0) &&
      (!result.value.as_consequent || result.value.as_consequent.length === 0)
    ) {
      ElMessage.info('当前商品暂无关联规则，请尝试其他商品名称。')
    }
  } catch (error) {
    ElMessage.error('查询失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <el-page-header @back="$router.push('/projects')" title="返回">
      <template #content>
        <span class="page-title">🔍 商品关联推荐</span>
      </template>
    </el-page-header>

    <div class="content">
      <el-card>
        <div class="search-row">
          <el-input
            v-model="keyword"
            placeholder="请输入商品名称，例如：椅子"
            clearable
            @keyup.enter="search"
            style="max-width: 420px"
          />
          <el-button type="primary" :loading="loading" @click="search">查询</el-button>
        </div>
      </el-card>

      <div v-if="result && (result.as_antecedent.length || result.as_consequent.length)" class="tables">
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <span>作为前项时的推荐</span>
            </div>
          </template>
          <div v-if="result.as_antecedent.length">
            <el-table :data="result.as_antecedent" style="width: 100%" stripe>
              <el-table-column label="前项" min-width="180">
                <template #default="{ row }">
                  <el-tag type="info" size="small" v-for="(it, idx) in row.from_items" :key="idx" class="tag">
                    {{ it }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="后项" min-width="140">
                <template #default="{ row }">
                  <el-tag type="success" size="small" v-for="(it, idx) in row.to_items" :key="idx" class="tag">
                    {{ it }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="支持度" width="100">
                <template #default="{ row }">{{ formatPercent(row.support) }}</template>
              </el-table-column>
              <el-table-column label="置信度" width="100">
                <template #default="{ row }">{{ formatPercent(row.confidence) }}</template>
              </el-table-column>
              <el-table-column label="提升度" width="90">
                <template #default="{ row }">{{ formatLift(row.lift) }}</template>
              </el-table-column>
              <el-table-column label="策略建议" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">{{ row.strategy }}</template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="暂无数据" />
        </el-card>

        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <span>作为后项时的推荐</span>
            </div>
          </template>
          <div v-if="result.as_consequent.length">
            <el-table :data="result.as_consequent" style="width: 100%" stripe>
              <el-table-column label="前项" min-width="180">
                <template #default="{ row }">
                  <el-tag type="info" size="small" v-for="(it, idx) in row.from_items" :key="idx" class="tag">
                    {{ it }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="后项" min-width="140">
                <template #default="{ row }">
                  <el-tag type="success" size="small" v-for="(it, idx) in row.to_items" :key="idx" class="tag">
                    {{ it }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="支持度" width="100">
                <template #default="{ row }">{{ formatPercent(row.support) }}</template>
              </el-table-column>
              <el-table-column label="置信度" width="100">
                <template #default="{ row }">{{ formatPercent(row.confidence) }}</template>
              </el-table-column>
              <el-table-column label="提升度" width="90">
                <template #default="{ row }">{{ formatLift(row.lift) }}</template>
              </el-table-column>
              <el-table-column label="策略建议" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">{{ row.strategy }}</template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="暂无数据" />
        </el-card>
      </div>

      <el-empty
        v-else-if="result && !result.as_antecedent.length && !result.as_consequent.length"
        description="当前商品暂无关联规则，请尝试其他商品名称。"
        style="margin-top: 2rem;"
      />
    </div>
  </div>
</template>

<style scoped>
.page-container {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 1.5rem;
  font-weight: bold;
}

.content {
  margin-top: 1.5rem;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.tables {
  margin-top: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.result-card {
  overflow-x: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.tag {
  margin-right: 6px;
  margin-bottom: 4px;
}

@media (max-width: 768px) {
  .search-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
