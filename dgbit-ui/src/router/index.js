import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue')
  },
  {
    path: '/trading',
    name: 'Trading',
    component: () => import('@/views/Trading.vue')
  },
  {
    path: '/portfolio',
    name: 'Portfolio',
    component: () => import('@/views/Portfolio.vue')
  },
  {
    path: '/strategies',
    name: 'Strategies',
    component: () => import('@/views/Strategies.vue')
  },
  {
    path: '/system',
    name: 'System',
    component: () => import('@/views/System.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
