import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/projects',
      name: 'projects',
      component: () => import('@/views/ProjectList.vue')
    },
    {
      path: '/projects/new',
      name: 'project-create',
      component: () => import('@/views/ProjectCreate.vue')
    },
    {
      path: '/projects/:id',
      name: 'project-detail',
      component: () => import('@/views/ProjectDetail.vue')
    },
    {
      path: '/me/projects',
      name: 'my-projects',
      component: () => import('@/views/MyProjects.vue')
    },
    {
      path: '/data-processing',
      name: 'data-processing',
      component: () => import('@/views/DataProcessing.vue')
    },
    {
      path: '/data-processing/jobs/:jobId',
      name: 'data-processing-job',
      component: () => import('@/views/DataProcessing.vue')
    },
    {
      path: '/projects/:id/recommend',
      name: 'product-recommend',
      component: () => import('@/views/ProductRecommend.vue')
    },
    {
      path: '/projects/:id/customer/:customerId',
      name: 'customer-analysis',
      component: () => import('@/views/CustomerAnalysis.vue')
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/Settings.vue')
    }
  ]
})

export default router
