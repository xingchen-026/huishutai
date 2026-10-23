<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
// 从 localStorage 读取登录时保存的用户名，用于欢迎语展示
const username = localStorage.getItem('username') || ''

// 退出登录：清除本地身份信息后跳回登录页
function logout() {
  localStorage.removeItem('user_id')
  localStorage.removeItem('username')
  router.push('/login')
}
</script>

<template>
  <div style="padding: 40px;">
    <h2>欢迎，{{ username }}</h2>
    <button @click="logout" style="margin-top: 20px; padding: 8px 16px; cursor: pointer;">
      退出登录
    </button>
  </div>
</template>
