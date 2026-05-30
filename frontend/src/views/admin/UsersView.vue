<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getAdminUsers, getAdminUserDetail,
  updateUserRole, updateUserStatus,
  type AdminUserListItem, type AdminUserDetail,
} from '@/api/admin'
import { Search, Shield, ShieldOff, UserCheck, UserX } from 'lucide-vue-next'

const users = ref<AdminUserListItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const searchQuery = ref('')
const selectedUser = ref<AdminUserDetail | null>(null)
const showDrawer = ref(false)
const actionError = ref<string | null>(null)

async function fetchUsers() {
  loading.value = true
  error.value = null
  try {
    users.value = await getAdminUsers(searchQuery.value || undefined)
  } catch (e: any) {
    error.value = e?.message || '获取用户列表失败'
  } finally {
    loading.value = false
  }
}

async function openUserDetail(userId: string) {
  try {
    selectedUser.value = await getAdminUserDetail(userId)
    showDrawer.value = true
    actionError.value = null
  } catch (e: any) {
    actionError.value = e?.message || '获取用户详情失败'
  }
}

function closeDrawer() {
  showDrawer.value = false
  selectedUser.value = null
}

async function changeRole(userId: string, newRole: 'user' | 'admin') {
  if (!confirm(`确定要将用户角色改为 "${newRole}" 吗？`)) return
  try {
    await updateUserRole(userId, newRole)
    await fetchUsers()
    if (selectedUser.value && selectedUser.value.id === userId) {
      selectedUser.value.role = newRole
    }
    actionError.value = null
  } catch (e: any) {
    actionError.value = e?.message || '修改角色失败'
  }
}

async function changeStatus(userId: string, newStatus: 'active' | 'disabled') {
  const label = newStatus === 'active' ? '启用' : '禁用'
  if (!confirm(`确定要${label}该用户吗？`)) return
  try {
    await updateUserStatus(userId, newStatus)
    await fetchUsers()
    if (selectedUser.value && selectedUser.value.id === userId) {
      selectedUser.value.status = newStatus
    }
    actionError.value = null
  } catch (e: any) {
    actionError.value = e?.message || '修改状态失败'
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="users-view">
    <h1 class="page-title">用户管理</h1>

    <!-- Search -->
    <div class="search-bar">
      <Search :size="16" class="search-icon" />
      <input v-model="searchQuery" placeholder="搜索邮箱或显示名称..." class="search-input" @input="fetchUsers" />
    </div>

    <div v-if="actionError" class="action-error">{{ actionError }}</div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <!-- Table -->
    <div v-else class="table-wrap">
      <table class="user-table">
        <thead>
          <tr>
            <th>邮箱</th>
            <th>显示名称</th>
            <th>角色</th>
            <th>状态</th>
            <th>项目数</th>
            <th>最后登录</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="users.length === 0">
            <td colspan="7" class="empty-row">暂无用户</td>
          </tr>
          <tr v-for="user in users" :key="user.id" @click="openUserDetail(user.id)" class="user-row">
            <td class="cell-email">{{ user.email }}</td>
            <td>{{ user.displayName || '-' }}</td>
            <td>
              <span class="role-badge" :class="user.role">
                <Shield v-if="user.role === 'admin'" :size="12" />
                <ShieldOff v-else :size="12" />
                {{ user.role === 'admin' ? '管理员' : '用户' }}
              </span>
            </td>
            <td>
              <span class="status-badge" :class="user.status">
                {{ user.status === 'active' ? '活跃' : '已禁用' }}
              </span>
            </td>
            <td>{{ user.projectCount }}</td>
            <td class="cell-time">{{ user.lastLoginAt ? new Date(user.lastLoginAt).toLocaleDateString() : '-' }}</td>
            <td class="cell-actions" @click.stop>
              <button
                v-if="user.role === 'user'"
                class="action-btn promote"
                @click="changeRole(user.id, 'admin')"
                title="提升为管理员"
              >
                <Shield :size="14" />
              </button>
              <button
                v-if="user.role === 'admin'"
                class="action-btn demote"
                @click="changeRole(user.id, 'user')"
                title="降级为用户"
              >
                <ShieldOff :size="14" />
              </button>
              <button
                v-if="user.status === 'active'"
                class="action-btn disable"
                @click="changeStatus(user.id, 'disabled')"
                title="禁用"
              >
                <UserX :size="14" />
              </button>
              <button
                v-if="user.status === 'disabled'"
                class="action-btn enable"
                @click="changeStatus(user.id, 'active')"
                title="启用"
              >
                <UserCheck :size="14" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Detail Drawer -->
    <div v-if="showDrawer" class="drawer-overlay" @click.self="closeDrawer">
      <div class="drawer">
        <button class="drawer-close" @click="closeDrawer">&times;</button>
        <h2 class="drawer-title">用户详情</h2>
        <div v-if="selectedUser" class="detail-body">
          <div class="detail-field">
            <span class="detail-label">ID</span>
            <span class="detail-value mono">{{ selectedUser.id }}</span>
          </div>
          <div class="detail-field">
            <span class="detail-label">邮箱</span>
            <span class="detail-value">{{ selectedUser.email }}</span>
          </div>
          <div class="detail-field">
            <span class="detail-label">显示名称</span>
            <span class="detail-value">{{ selectedUser.displayName || '-' }}</span>
          </div>
          <div class="detail-field">
            <span class="detail-label">角色</span>
            <span class="detail-value">{{ selectedUser.role === 'admin' ? '管理员' : '用户' }}</span>
          </div>
          <div class="detail-field">
            <span class="detail-label">状态</span>
            <span class="detail-value">{{ selectedUser.status === 'active' ? '活跃' : '已禁用' }}</span>
          </div>
          <hr class="divider" />
          <h3>项目列表 ({{ selectedUser.projectCount }})</h3>
          <div v-if="selectedUser.projects.length === 0" class="no-projects">暂无项目</div>
          <div v-for="proj in selectedUser.projects" :key="proj.id" class="project-item">
            <span class="proj-name">{{ proj.name }}</span>
            <span class="proj-status">{{ proj.status }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 24px;
}

html.dark .page-title { color: #f1f5f9; }

.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 10px;
  background: #fff;
  margin-bottom: 16px;
  max-width: 360px;
}

html.dark .search-bar { background: #1a1a20; border-color: rgba(255,255,255,0.08); }

.search-icon { color: #94a3b8; flex-shrink: 0; }

.search-input {
  border: none;
  background: none;
  font-size: 0.85rem;
  color: #475569;
  width: 100%;
  outline: none;
}

html.dark .search-input { color: #cbd5e1; }

.action-error {
  padding: 8px 14px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
  font-size: 0.85rem;
  margin-bottom: 12px;
}

.table-wrap {
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 14px;
  overflow: hidden;
}

html.dark .table-wrap { background: #1a1a20; border-color: rgba(255,255,255,0.06); }

.user-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.user-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.user-table td {
  padding: 10px 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
  color: #475569;
}

html.dark .user-table td { color: #cbd5e1; border-color: rgba(255,255,255,0.04); }

.user-row { cursor: pointer; transition: background 120ms; }
.user-row:hover { background: rgba(99, 102, 241, 0.04); }

.empty-row { text-align: center; color: #94a3b8; }

.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.role-badge.admin { background: rgba(99, 102, 241, 0.1); color: #6366f1; }
.role-badge.user { background: rgba(148, 163, 184, 0.1); color: #64748b; }

.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge.active { background: rgba(16, 185, 129, 0.1); color: #059669; }
.status-badge.disabled { background: rgba(239, 68, 68, 0.1); color: #dc2626; }

.cell-email { font-weight: 500; }
.cell-time { white-space: nowrap; color: #94a3b8; font-size: 0.8rem; }

.cell-actions { display: flex; gap: 4px; }

.action-btn {
  width: 30px;
  height: 30px;
  border-radius: 7px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #fff;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 160ms ease;
}

html.dark .action-btn { background: #2a2a30; border-color: rgba(255,255,255,0.06); color: #cbd5e1; }

.action-btn.promote:hover { background: rgba(99, 102, 241, 0.1); color: #6366f1; border-color: rgba(99, 102, 241, 0.3); }
.action-btn.demote:hover { background: rgba(245, 158, 11, 0.1); color: #d97706; border-color: rgba(245, 158, 11, 0.3); }
.action-btn.disable:hover { background: rgba(239, 68, 68, 0.1); color: #dc2626; border-color: rgba(239, 68, 68, 0.3); }
.action-btn.enable:hover { background: rgba(16, 185, 129, 0.1); color: #059669; border-color: rgba(16, 185, 129, 0.3); }

/* Drawer */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 200;
  display: flex;
  justify-content: flex-end;
}

.drawer {
  width: 420px;
  background: #fff;
  height: 100%;
  padding: 32px;
  overflow-y: auto;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.1);
}

html.dark .drawer { background: #1a1a20; }

.drawer-close {
  float: right;
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #94a3b8;
  cursor: pointer;
}

.drawer-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 24px;
}

html.dark .drawer-title { color: #f1f5f9; }

.detail-field {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
}

.detail-label { font-size: 0.82rem; color: #94a3b8; }
.detail-value { font-size: 0.85rem; color: #475569; font-weight: 500; }
html.dark .detail-value { color: #cbd5e1; }

.mono { font-family: monospace; font-size: 0.78rem; }

.divider { margin: 20px 0; border: none; border-top: 1px solid rgba(15, 23, 42, 0.06); }

.drawer h3 {
  font-size: 0.9rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 12px;
}

html.dark .drawer h3 { color: #f1f5f9; }

.no-projects { font-size: 0.85rem; color: #94a3b8; padding: 8px 0; }

.project-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.02);
  margin-bottom: 4px;
}

.proj-name { font-size: 0.85rem; color: #475569; font-weight: 500; }
.proj-status { font-size: 0.72rem; color: #94a3b8; }

.loading-state, .error-state {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
}
.error-state { color: #EF4444; }
</style>
