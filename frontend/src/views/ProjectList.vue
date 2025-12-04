<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const router = useRouter()

interface Project {
  id: string
  name: string
  description?: string
  dataset_filename?: string
  status: string
  created_at: string
  updated_at: string
}

const projects = ref<Project[]>([])
const loading = ref(false)
const total = ref(0)

// 加载项目列表
const loadProjects = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/projects')
    if (response.data.success) {
      projects.value = response.data.data
      total.value = response.data.total
    }
  } catch (error) {
    ElMessage.error('加载项目列表失败')
  } finally {
    loading.value = false
  }
}

// 新建项目
const createProject = () => {
  router.push('/projects/new')
}

// 查看详情
const viewProject = (id: string) => {
  router.push(`/projects/${id}`)
}

// 删除项目
const deleteProject = async (id: string, name: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目 "${name}" 吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    const response = await axios.delete(`/api/projects/${id}`)
    if (response.data.success) {
      ElMessage.success('删除成功')
      loadProjects()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 获取状态类型
const getStatusType = (status: string) => {
  const typeMap: Record<string, string> = {
    '待处理': 'info',
    '处理中': 'warning',
    '已完成': 'success',
    '失败': 'danger'
  }
  return typeMap[status] || 'info'
}

onMounted(() => {
  loadProjects()
})
</script>

<template>
  <div class="page-container">
    <el-page-header @back="$router.push('/')" title="返回">
      <template #content>
        <span class="page-title">📋 项目列表</span>
      </template>
      <template #extra>
        <el-button type="primary" @click="createProject">
          ➕ 新建项目
        </el-button>
      </template>
    </el-page-header>

    <div class="content">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>全部项目 ({{ total }})</span>
          </div>
        </template>

        <el-table
          :data="projects"
          v-loading="loading"
          style="width: 100%"
          :default-sort="{ prop: 'created_at', order: 'descending' }"
        >
          <el-table-column prop="name" label="项目名称" min-width="180">
            <template #default="{ row }">
              <el-link @click="viewProject(row.id)" type="primary">
                {{ row.name }}
              </el-link>
            </template>
          </el-table-column>

          <el-table-column prop="dataset_filename" label="数据集" min-width="150">
            <template #default="{ row }">
              <span v-if="row.dataset_filename">{{ row.dataset_filename }}</span>
              <span v-else style="color: #999;">未上传</span>
            </template>
          </el-table-column>

          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="created_at" label="创建时间" width="180" sortable>
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>

          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewProject(row.id)">
                查看详情
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="deleteProject(row.id, row.name)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!loading && projects.length === 0"
          description="暂无项目，点击右上角新建项目"
        />
      </el-card>
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
  margin-top: 2rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
</style>
