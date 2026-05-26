<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/utils/http'
import { Search, Delete, Folder, Plus, FolderOpened, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()

interface Project {
  id: string
  name: string
  description?: string
  dataset_filename?: string
  dataset_ref?: { name?: string } | null
  status: string
  created_at: string
  updated_at: string
}

const projects = ref<Project[]>([])
const loading = ref(false)
const searchQuery = ref('')

// Load projects
const loadProjects = async () => {
  loading.value = true
  try {
    const response = await http.get('/api/analysis/projects')
    if (response.data.success) {
      projects.value = response.data.data.projects
    }
  } catch (error) {
    ElMessage.error('无法获取项目数据')
  } finally {
    loading.value = false
  }
}

const createProject = () => {
  router.push('/projects/new')
}

const viewProject = (id: string) => {
  router.push(`/projects/${id}`)
}

const deleteProject = async (e: Event, id: string, name: string) => {
  e.stopPropagation() // Prevent card click
  try {
    await ElMessageBox.confirm(
      `确定要删除 "${name}" 吗？数据将无法恢复。`,
      '确认操作',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    const response = await http.delete(`/api/analysis/projects/${id}`)
    if (response.data.success) {
      ElMessage.success('项目已删除')
      loadProjects()
    }
  } catch (error: any) {
    // cancelled
  }
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Status Styling
const getStatusConfig = (status: string) => {
  const map: Record<string, { color: string, label: string }> = {
    queued: { color: '#9CA3AF', label: '待处理' },
    processing: { color: '#F59E0B', label: '进行中' },
    completed: { color: '#10B981', label: '已完成' },
    failed: { color: '#EF4444', label: '失败' },
    '待处理': { color: '#9CA3AF', label: '待处理' },
    '处理中': { color: '#F59E0B', label: '进行中' },
    '已完成': { color: '#10B981', label: '已完成' },
    '失败': { color: '#EF4444', label: '失败' }
  }
  return map[status] || { color: '#9CA3AF', label: status }
}

onMounted(() => {
  loadProjects()
})
</script>

<template>
  <div class="container-breath">
    <!-- Header -->
    <header class="page-header">
      <div>
        <h1 class="text-display" style="font-size: 2rem; margin-bottom: 8px;">项目空间</h1>
        <p class="text-subtitle">管理您的所有分析任务</p>
      </div>

      <div class="header-actions">
        <!-- Search Pill -->
        <div class="search-pill">
          <el-icon class="search-icon"><Search /></el-icon>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索项目..."
            class="search-input"
          >
        </div>

        <el-button type="primary" class="btn-create" @click="createProject" round>
          <el-icon style="margin-right: 4px"><Plus /></el-icon> 新建项目
        </el-button>
      </div>
    </header>

    <!-- Project Grid -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <div v-else-if="projects.length > 0" class="project-grid">
      <div
        v-for="project in projects"
        :key="project.id"
        class="project-card"
        @click="viewProject(project.id)"
      >
        <!-- Card Header -->
        <div class="card-top">
          <div class="status-badge" :style="{ backgroundColor: getStatusConfig(project.status).color + '20', color: getStatusConfig(project.status).color }">
            <span class="status-dot" :style="{ backgroundColor: getStatusConfig(project.status).color }"></span>
            {{ getStatusConfig(project.status).label }}
          </div>
          <button class="btn-icon-only" @click="(e) => deleteProject(e, project.id, project.name)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>

        <!-- Card Body -->
        <div class="card-body">
          <h3 class="project-title">{{ project.name }}</h3>
          <p class="project-meta">
            <el-icon class="meta-icon"><Folder /></el-icon>
            {{ project.dataset_filename || project.dataset_ref?.name || '无数据集' }}
          </p>
        </div>

        <!-- Card Footer -->
        <div class="card-footer">
          <span class="time-tag">{{ formatDate(project.created_at) }}</span>
          <el-icon class="arrow-icon"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <el-icon class="empty-icon"><FolderOpened /></el-icon>
      <h3>暂无项目</h3>
      <p>开始您的第一个数据分析任务吧</p>
      <el-button type="primary" @click="createProject" style="margin-top: 24px;">创建项目</el-button>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 48px;
  flex-wrap: wrap;
  gap: 24px;
}

.header-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}

.search-pill {
  background: var(--color-surface);
  border-radius: var(--radius-pill);
  padding: 8px 16px;
  display: flex;
  align-items: center;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s ease;
  width: 240px;
}

.search-pill:focus-within {
  box-shadow: var(--shadow-glow);
  border-color: var(--color-accent);
  width: 280px;
}

.search-icon {
  opacity: 0.5;
  margin-right: 10px;
  font-size: 1.1rem;
  color: var(--text-secondary);
}

.search-input {
  border: none;
  background: transparent;
  outline: none;
  font-family: inherit;
  font-size: 0.95rem;
  width: 100%;
  color: var(--text-primary);
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.project-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 24px;
  position: relative;
  transition: all 0.3s var(--ease-spring);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  height: 200px;
}

.project-card:hover {
  transform: translateY(-8px);
  box-shadow: var(--shadow-md);
  z-index: 5;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.status-badge {
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-size: 0.75rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.btn-icon-only {
  background: transparent;
  border: none;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s ease;
  font-size: 1rem;
  padding: 4px;
  border-radius: 4px;
}

.btn-icon-only:hover {
  background: rgba(0,0,0,0.05);
}

.project-card:hover .btn-icon-only {
  opacity: 0.4;
}
.project-card:hover .btn-icon-only:hover {
  opacity: 1;
}

.card-body {
  flex: 1;
}

.project-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: var(--text-primary);
}

.project-meta {
  font-size: 0.9rem;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-icon {
  opacity: 0.7;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}

.time-tag {
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.arrow-icon {
  color: var(--color-accent);
  opacity: 0;
  transform: translateX(-10px);
  transition: all 0.3s ease;
  font-weight: bold;
}

.project-card:hover .arrow-icon {
  opacity: 1;
  transform: translateX(0);
}

.empty-state {
  text-align: center;
  padding: 80px 0;
  opacity: 0.6;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 16px;
  opacity: 0.5;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0,0,0,0.1);
  border-radius: 50%;
  border-top-color: var(--color-accent);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
