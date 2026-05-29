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
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/Settings.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  // Wait for auth initialization on first load
  if (authStore.status === 'idle' && authStore.accessToken) {
    authStore.loadMe().finally(() => {
      next({ ...to, replace: true })
    })
    return
  }

  const requiresAuth = to.meta.requiresAuth
  const guestOnly = to.meta.guestOnly

  if (requiresAuth && !authStore.isAuthenticated) {
    authStore.setReturnTo(to.fullPath)
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  if (guestOnly && authStore.isAuthenticated) {
    const redirect = (to.query.redirect as string) || '/projects'
    next({ path: redirect })
    return
  }

  next()
})

export default router
