import { createRouter, createWebHistory } from 'vue-router'
import DashBoard from '@/views/DashBoard.vue'
import DialogPage from '@/views/DialogPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dialogpage',
      component: DialogPage,
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashBoard,
    },
  ],
})

export default router
