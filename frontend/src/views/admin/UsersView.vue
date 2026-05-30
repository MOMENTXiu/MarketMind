<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getAdminUsers, getAdminUserDetail,
  updateUserRole, updateUserStatus,
  type AdminUserListItem, type AdminUserDetail,
} from '@/api/admin'
import { Search, Shield, ShieldOff, UserX, UserCheck } from 'lucide-vue-next'

const users = ref<AdminUserListItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const searchQuery = ref('')
const selectedUser = ref<AdminUserDetail | null>(null)
const showDrawer = ref(false)
const actionError = ref<string | null>(null)

async function fetchUsers() {
  loading.value = true; error.value = null
  try {
    users.value = await getAdminUsers(searchQuery.value || undefined)
  } catch (e: any) {
    error.value = e?.message || '获取用户列表失败'
  } finally { loading.value = false }
}

async function openUserDetail(userId: string) {
  try {
    selectedUser.value = await getAdminUserDetail(userId)
    showDrawer.value = true; actionError.value = null
  } catch (e: any) {
    actionError.value = e?.message || '获取用户详情失败'
  }
}

function closeDrawer() { showDrawer.value = false; selectedUser.value = null }

async function changeRole(userId: string, newRole: 'user' | 'admin') {
  if (!confirm(`确定要将用户角色改为 "${newRole}" 吗？`)) return
  try {
    await updateUserRole(userId, newRole); await fetchUsers()
    if (selectedUser.value?.id === userId) selectedUser.value.role = newRole
    actionError.value = null
  } catch (e: any) { actionError.value = e?.message || '修改角色失败' }
}

async function changeStatus(userId: string, newStatus: 'active' | 'disabled') {
  const label = newStatus === 'active' ? '启用' : '禁用'
  if (!confirm(`确定要${label}该用户吗？`)) return
  try {
    await updateUserStatus(userId, newStatus); await fetchUsers()
    if (selectedUser.value?.id === userId) selectedUser.value.status = newStatus
    actionError.value = null
  } catch (e: any) { actionError.value = e?.message || '修改状态失败' }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="users-view">
    <header class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-sub">管理系统用户、角色与访问权限</p>
      </div>
    </header>

    <!-- Search -->
    <div class="search-box">
      <Search class="w-3.5 h-3.5 search-icon" />
      <input v-model="searchQuery" placeholder="搜索邮箱或显示名称..." @input="fetchUsers" />
    </div>

    <div v-if="actionError" class="action-error">{{ actionError }}</div>
    <div v-if="loading" class="loading-state"><div class="spinner"></div></div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <!-- Table -->
    <div v-else class="table-wrap">
      <table class="user-table">
        <thead>
          <tr><th>邮箱</th><th>显示名称</th><th>角色</th><th>状态</th><th>项目数</th><th>最后登录</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-if="users.length === 0"><td colspan="7" class="empty-row">暂无用户</td></tr>
          <tr v-for="user in users" :key="user.id" @click="openUserDetail(user.id)" class="user-row">
            <td class="cell-email">{{ user.email }}</td>
            <td>{{ user.displayName || '-' }}</td>
            <td>
              <span class="role-badge" :class="user.role">
                <Shield v-if="user.role==='admin'" class="w-3 h-3" />
                <ShieldOff v-else class="w-3 h-3" />
                {{ user.role === 'admin' ? '管理员' : '用户' }}
              </span>
            </td>
            <td><span class="status-badge" :class="user.status">{{ user.status === 'active' ? '活跃' : '已禁用' }}</span></td>
            <td>{{ user.projectCount }}</td>
            <td class="cell-time">{{ user.lastLoginAt ? new Date(user.lastLoginAt).toLocaleDateString() : '-' }}</td>
            <td class="cell-actions" @click.stop>
              <button v-if="user.role==='user'" class="action-btn promote" @click="changeRole(user.id,'admin')" title="提升为管理员"><Shield class="w-3.5 h-3.5" /></button>
              <button v-if="user.role==='admin'" class="action-btn demote" @click="changeRole(user.id,'user')" title="降级为用户"><ShieldOff class="w-3.5 h-3.5" /></button>
              <button v-if="user.status==='active'" class="action-btn disable" @click="changeStatus(user.id,'disabled')" title="禁用"><UserX class="w-3.5 h-3.5" /></button>
              <button v-if="user.status==='disabled'" class="action-btn enable" @click="changeStatus(user.id,'active')" title="启用"><UserCheck class="w-3.5 h-3.5" /></button>
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
          <div class="detail-field"><span class="detail-label">ID</span><span class="detail-value mono">{{ selectedUser.id }}</span></div>
          <div class="detail-field"><span class="detail-label">邮箱</span><span class="detail-value">{{ selectedUser.email }}</span></div>
          <div class="detail-field"><span class="detail-label">显示名称</span><span class="detail-value">{{ selectedUser.displayName || '-' }}</span></div>
          <div class="detail-field"><span class="detail-label">角色</span><span class="detail-value">{{ selectedUser.role === 'admin' ? '管理员' : '用户' }}</span></div>
          <div class="detail-field"><span class="detail-label">状态</span><span class="detail-value">{{ selectedUser.status === 'active' ? '活跃' : '已禁用' }}</span></div>
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
.page-header { margin-bottom: 28px; }
.page-title { font-size: 1.75rem; font-weight: 800; color: var(--text-primary); margin: 0 0 4px 0; letter-spacing: -0.02em; }
.page-sub { font-size: 0.9rem; color: var(--text-tertiary); margin: 0; }

/* ─── search ─── */
.search-box {
  display: flex; align-items: center; gap: 10px; height: 48px; max-width: 360px;
  padding: 0 16px; border-radius: 20px; border: 1px solid var(--border-subtle);
  background: var(--color-surface); box-shadow: var(--shadow-xs);
  margin-bottom: 20px; transition: border-color 0.2s, box-shadow 0.2s;
}
.search-box:focus-within { border-color: rgba(99,102,241,0.35); box-shadow: 0 0 0 3px rgba(99,102,241,0.06); }
.search-icon { color: var(--text-tertiary); flex-shrink: 0; }
.search-box input { border: none; background: transparent; outline: none; flex: 1; min-width: 0; font-size: 0.9rem; color: var(--text-primary); }
.search-box input::placeholder { color: var(--text-tertiary); }

.action-error { padding: 10px 16px; border-radius: 12px; background: rgba(239,68,68,0.06); color: #dc2626; font-size: 0.85rem; margin-bottom: 14px; border: 1px solid rgba(239,68,68,0.08); }

/* ─── table ─── */
.table-wrap {
  background: var(--color-surface); border: 1px solid var(--border-subtle);
  border-radius: 20px; overflow: hidden; box-shadow: var(--shadow-xs);
}
.user-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.user-table th {
  text-align: left; padding: 14px 18px; font-size: 0.72rem; font-weight: 600;
  color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-subtle); background: var(--color-surface-hover);
}
.user-table td { padding: 11px 18px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); }
tr:last-child td { border-bottom: none; }
.user-row { cursor: pointer; transition: background 0.12s; }
.user-row:hover td { background: var(--color-surface-hover); }
.empty-row { text-align: center; color: var(--text-tertiary); padding: 32px 18px !important; }
.cell-email { font-weight: 500; color: var(--text-primary); }
.cell-time { white-space: nowrap; color: var(--text-tertiary); font-size: 0.8rem; }

/* ─── badges ─── */
.role-badge, .status-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 600;
}
.role-badge.admin { background: rgba(99,102,241,0.07); color: #6366F1; }
.role-badge.user { background: rgba(148,163,184,0.08); color: var(--text-tertiary); }
.status-badge.active { background: rgba(16,185,129,0.06); color: #059669; }
.status-badge.disabled { background: rgba(239,68,68,0.05); color: #dc2626; }

/* ─── action buttons ─── */
.cell-actions { display: flex; gap: 4px; }
.action-btn {
  width: 32px; height: 32px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border-subtle); background: transparent; color: var(--text-tertiary);
  cursor: pointer; transition: all 0.15s ease;
}
.action-btn:hover { border-color: transparent; }
.action-btn.promote:hover { background: rgba(99,102,241,0.1); color: #6366F1; }
.action-btn.demote:hover { background: rgba(245,158,11,0.1); color: #D97706; }
.action-btn.disable:hover { background: rgba(239,68,68,0.08); color: #dc2626; }
.action-btn.enable:hover { background: rgba(16,185,129,0.08); color: #059669; }

/* ─── drawer ─── */
.drawer-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 200; display: flex; justify-content: flex-end; }
.drawer {
  width: 420px; background: var(--color-surface); height: 100%; padding: 32px;
  overflow-y: auto; box-shadow: -4px 0 32px rgba(0,0,0,0.08);
}
.drawer-close { float: right; background: none; border: none; font-size: 1.5rem; color: var(--text-tertiary); cursor: pointer; }
.drawer-title { font-size: 1.25rem; font-weight: 700; color: var(--text-primary); margin: 0 0 24px; letter-spacing: -0.02em; }
.detail-field { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border-subtle); }
.detail-label { font-size: 0.82rem; color: var(--text-tertiary); }
.detail-value { font-size: 0.85rem; color: var(--text-primary); font-weight: 500; }
.mono { font-family: 'SF Mono', monospace; font-size: 0.78rem; }
.divider { margin: 20px 0; border: none; border-top: 1px solid var(--border-subtle); }
.drawer h3 { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); margin: 0 0 12px; }
.no-projects { font-size: 0.85rem; color: var(--text-tertiary); padding: 8px 0; }
.project-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-radius: 12px; background: var(--color-surface-hover); margin-bottom: 4px; }
.proj-name { font-size: 0.85rem; color: var(--text-primary); font-weight: 500; }
.proj-status { font-size: 0.72rem; color: var(--text-tertiary); }

.loading-state { display: flex; justify-content: center; padding: 60px 0; }
.spinner { width: 36px; height: 36px; border: 3px solid var(--border-subtle); border-radius: 50%; border-top-color: #6366F1; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-state { text-align: center; padding: 60px 0; color: #EF4444; font-size: 0.9rem; }
</style>
