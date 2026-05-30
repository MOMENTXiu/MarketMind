import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
      meta: { public: true }
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { guestOnly: true }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/Register.vue'),
      meta: { guestOnly: true }
    },
    {
      path: '/projects',
      name: 'projects',
      component: () => import('@/views/ProjectList.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/projects/new',
      name: 'project-create',
      component: () => import('@/views/ProjectCreate.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/projects/:id',
      name: 'project-detail',
      component: () => import('@/views/ProjectDetail.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/me/projects',
      name: 'my-projects',
      component: () => import('@/views/MyProjects.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/data-processing',
      name: 'data-processing',
      component: () => import('@/views/DataProcessing.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/data-processing/jobs/:jobId',
      name: 'data-processing-job',
      component: () => import('@/views/DataProcessing.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/projects/:id/recommend',
      name: 'product-recommend',
      component: () => import('@/views/ProductRecommend.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/projects/:id/customer/:customerId',
      name: 'customer-analysis',
      component: () => import('@/views/CustomerAnalysis.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/project-intro',
      name: 'project-intro',
      component: () => import('@/views/ProjectIntro.vue'),
      meta: { public: true }
    },
    {
      path: '/me/profile',
      name: 'user-profile',
      component: () => import('@/views/UserProfile.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      redirect: '/admin/settings'
    },
    {
      path: '/admin',
      component: () => import('@/views/admin/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        {
          path: '',
          redirect: '/admin/status'
        },
        {
          path: 'status',
          name: 'admin-status',
          component: () => import('@/views/admin/StatusDashboard.vue'),
        },
        {
          path: 'settings',
          name: 'admin-settings',
          component: () => import('@/views/admin/SettingsView.vue'),
        },
        {
          path: 'logs',
          name: 'admin-logs',
          component: () => import('@/views/admin/LogsView.vue'),
        },
        {
          path: 'users',
          name: 'admin-users',
          component: () => import('@/views/admin/UsersView.vue'),
        },
      ]
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next({ path: '/projects' })
    return
  }

  next()
})

export default router
