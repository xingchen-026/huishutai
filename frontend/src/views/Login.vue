<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '@/api/user'
import { setAuth } from '@/utils/auth'

const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function onSubmit() {
  errorMsg.value = ''

  if (!username.value.trim()) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (!password.value) {
    errorMsg.value = '请输入密码'
    return
  }

  loading.value = true
  try {
    const res = await login(username.value.trim(), password.value)
    if (res.code !== 0) {
      errorMsg.value = res.message || '登录失败'
      return
    }

    setAuth(res.data.token, {
      user_id: res.data.user_id,
      username: res.data.username,
    })

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    if (redirect.startsWith('/') && !redirect.startsWith('//')) {
      router.push(redirect)
    } else {
      router.push('/home')
    }
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.message || '网络错误，请稍后再试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-center">
    <div class="card">
      <h2>汇书台登录</h2>
      <p class="subtitle">登录后继续使用</p>

      <form @submit.prevent="onSubmit">
        <div class="form-item">
          <label for="login-username">用户名</label>
          <input
            id="login-username"
            v-model="username"
            autocomplete="username"
            placeholder="请输入用户名"
          />
        </div>

        <div class="form-item">
          <label for="login-password">密码</label>
          <input
            id="login-password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
          />
        </div>

        <p v-if="errorMsg" class="form-error">{{ errorMsg }}</p>

        <button class="btn" type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登 录' }}
        </button>
      </form>

      <p class="switch-line">
        还没有账号？
        <router-link class="link" to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>