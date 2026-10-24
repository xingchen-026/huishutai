import axios from 'axios'
import { clearAuth, getToken } from '@/utils/auth'

const request = axios.create({
  baseURL: '/api', // 开发环境由 vite proxy 去掉 /api 前缀
  timeout: 10000,
})

// 请求拦截：有 token 就自动带上
request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})


// 响应拦截：直接返回后端的 {code, message, data}
// 401 表示 token 无效/过期：清本地登录态并回登录页
request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      clearAuth()
      const path = window.location.pathname
      if (path !== '/login' && path !== '/register') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(err)
  },
)

export default request