import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/video-workbench'
    },
    {
      path: '/video-workbench',
      name: 'video-workbench',
      component: () => import('../views/VideoWorkbench.vue')
    }
  ]
})

export default router

