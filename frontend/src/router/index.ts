import { createRouter, createWebHistory } from 'vue-router'
// @ts-expect-error Vue SFC type declarations may not be available to TypeScript here.
import Login from '@/views/Login.vue'
// @ts-expect-error Vue SFC type declarations may not be available to TypeScript here.
import Home from '@/views/Home.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'login', component: Login },
    { path: '/home', name: 'home', component: Home },
  ],
})

// 简单的登录守卫：没登录就跳回登录页
router.beforeEach((to) => {
  const token = localStorage.getItem('user_id')
  if (!token && to.name !== 'login') {
    return { name: 'login' }
  }
})

export default router
