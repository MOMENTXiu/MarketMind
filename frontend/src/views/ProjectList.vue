<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Trash2, Folder, Plus, FolderOpen, ArrowRight } from 'lucide-vue-next'
import {
  deleteRetailProject,
  getApiErrorMessage,
  getRetailProjectStatusConfig,
  listRetailProjects,
  type RetailProject
} from '../api'

const router = useRouter()

const projects = ref<RetailProject[]>([])
const loading = ref(false)
const searchQuery = ref('')

// Load projects
const loadProjects = async () => {
  loading.value = true
  try {
    const result = await listRetailProjects()
    projects.value = result.projects
  } catch (error) {
    ElMessage.error(`无法获取项目数据: ${getApiErrorMessage(error)}`)
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

    await deleteRetailProject(id)
    ElMessage.success('项目已删除')
    await loadProjects()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(`删除失败: ${getApiErrorMessage(error)}`)
    }
  }
}

const formatDate = (dateStr?: string | null) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusConfig = (status: string) => getRetailProjectStatusConfig(status)

onMounted(() => {
  loadProjects()
})
</script>

<template>
  <div class="container-breath">
    <header class="page-header">
      <div>
        <h1 class="page-title">项目空间</h1>
        <p class="page-sub">管理您的所有分析任务</p>
      </div>
      <div class="header-actions">
        <div class="search-box">
          <Search class="h-3.5 w-3.5" />
          <input v-model="searchQuery" type="text" placeholder="搜索项目..." />
        </div>
        <button class="btn-create" @click="createProject">
          <Plus class="h-3.5 w-3.5" />新建项目
        </button>
      </div>
    </header>

    <div v-if="loading" class="loading-state"><div class="spinner"></div></div>

    <div v-else-if="projects.length > 0" class="project-grid">
      <article
        v-for="project in projects"
        :key="project.id"
        class="project-card group"
        @click="viewProject(project.id)"
      >
        <div class="card-top">
          <div class="card-badges">
            <span class="status-badge" :style="{ backgroundColor: getStatusConfig(project.status).color + '18', color: getStatusConfig(project.status).color }">
              <span class="status-dot" :style="{ backgroundColor: getStatusConfig(project.status).color }"></span>
              {{ getStatusConfig(project.status).label }}
            </span>
            <span v-if="project.analysis_kind === 'data_processing'" class="kind-badge kind-dp">通用诊断</span>
            <span v-else class="kind-badge kind-retail">零售分析</span>
          </div>
          <div class="action-slot">
            <button class="btn-delete" @click="(e) => deleteProject(e, project.id, project.name)">
              <Trash2 class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div class="card-body">
          <h3 class="card-title">{{ project.name }}</h3>
          <p v-if="project.description" class="card-desc">{{ project.description }}</p>
          <div class="card-meta">
            <Folder class="h-3.5 w-3.5" />
            <span>{{ project.dataset_filename || project.dataset_ref?.name || '暂无数据文件' }}</span>
          </div>
        </div>

        <div class="card-footer">
          <span>{{ formatDate(project.created_at) }}</span>
          <div class="arrow-slot">
            <ArrowRight class="h-3.5 w-3.5" />
          </div>
        </div>
      </article>
    </div>

    <div v-else class="empty-state">
      <FolderOpen class="empty-icon" />
      <h3>暂无项目</h3>
      <p>开始您的第一个数据分析任务吧</p>
      <el-button type="primary" @click="createProject" style="margin-top: 24px">创建项目</el-button>
    </div>
  </div>
</template>

<style scoped>
/* ─── header ─── */
.page-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 40px; flex-wrap: wrap; gap: 20px; }
.page-title { font-size: 1.75rem; font-weight: 800; color: var(--text-primary); margin: 0 0 4px 0; }
.page-sub { font-size: 0.9rem; color: var(--text-tertiary); margin: 0; }
.header-actions { display: flex; align-items: center; gap: 16px; }

/* ─── search box ─── */
.search-box {
  display: flex; align-items: center; gap: 10px;
  height: 48px; width: 320px;
  padding: 0 16px;
  border-radius: 20px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--border-subtle, rgba(15,23,42,0.06));
  color: var(--text-secondary);
  box-shadow: 0 8px 24px rgba(15,23,42,0.03);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.search-box:focus-within { border-color: rgba(99,102,241,0.4); box-shadow: 0 12px 32px rgba(99,102,241,0.08); }
.search-box input {
  border: none; background: transparent; outline: none;
  flex: 1; min-width: 0;
  font-size: 0.9rem; color: var(--text-primary);
}
.search-box input::placeholder { color: var(--text-tertiary); }

/* ─── create button ─── */
.btn-create {
  display: inline-flex; align-items: center; gap: 8px;
  height: 48px; padding: 0 20px;
  border-radius: 20px; border: none;
  background: #6366F1; color: #fff;
  font-size: 0.9rem; font-weight: 600;
  box-shadow: 0 10px 24px rgba(99,102,241,0.22);
  cursor: pointer; transition: transform 0.15s, box-shadow 0.15s;
}
.btn-create:hover { transform: translateY(-1px); box-shadow: 0 14px 32px rgba(99,102,241,0.28); }

/* ─── grid ─── */
.project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }

/* ─── card ─── */
.project-card {
  display: flex; flex-direction: column;
  min-height: 240px; padding: 28px;
  border-radius: 28px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--border-subtle, rgba(15,23,42,0.06));
  box-shadow: 0 12px 32px rgba(15,23,42,0.03);
  cursor: pointer;
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
}
.project-card:hover {
  transform: translateY(-2px);
  border-color: rgba(99,102,241,0.25);
  box-shadow: 0 20px 48px rgba(15,23,42,0.07);
}

/* top row */
.card-top { display: flex; justify-content: space-between; align-items: flex-start; }
.card-badges { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.status-badge { display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 12px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.kind-badge { display: inline-flex; align-items: center; height: 28px; padding: 0 12px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }
.kind-dp { background: rgba(99,102,241,0.07); color: #6366F1; }
.kind-retail { background: rgba(15,23,42,0.04); color: var(--text-tertiary); }

/* action slot (always occupies space) */
.action-slot { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; }
.btn-delete {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: 8px; border: none;
  background: transparent; color: var(--text-tertiary);
  cursor: pointer; opacity: 0; transition: opacity 0.15s, background 0.15s, color 0.15s;
}
.project-card:hover .btn-delete { opacity: 0.5; }
.btn-delete:hover { background: rgba(239,68,68,0.08); color: #EF4444; opacity: 1 !important; }

/* body */
.card-body { flex: 1; padding-top: 28px; min-height: 82px; }
.card-title { font-size: 1.2rem; font-weight: 700; color: var(--text-primary); margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 1.25; }
.card-desc { font-size: 0.82rem; color: var(--text-tertiary); margin: 6px 0 0 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-meta { display: flex; align-items: center; gap: 6px; margin-top: 10px; font-size: 0.82rem; color: var(--text-tertiary); }
.card-meta span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* footer */
.card-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: auto; padding-top: 16px;
  border-top: 1px solid var(--border-subtle, rgba(15,23,42,0.06));
  font-size: 0.82rem; color: var(--text-tertiary);
}
.arrow-slot { display: flex; align-items: center; justify-content: center; width: 20px; height: 20px; }
.arrow-slot svg { opacity: 0; transition: opacity 0.2s, transform 0.2s; color: var(--text-tertiary); }
.project-card:hover .arrow-slot svg { opacity: 0.5; transform: translateX(2px); }

/* ─── empty & loading ─── */
.empty-state { text-align: center; padding: 80px 0; color: var(--text-tertiary); }
.empty-icon { width: 40px; height: 40px; margin: 0 auto 12px; opacity: 0.35; }
.loading-state { display: flex; justify-content: center; padding: 60px 0; }
.spinner { width: 36px; height: 36px; border: 3px solid var(--border-subtle); border-radius: 50%; border-top-color: #6366F1; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
