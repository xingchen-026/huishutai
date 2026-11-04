<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/ui/AppIcon.vue'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import { login } from '@/api/user'
import { getErrorMessage } from '@/utils/error'

const route = useRoute()
const router = useRouter()
const theme = useThemeStore()
const auth = useAuthStore()

const isDark = computed(() => theme.isDark)
const toggleTheme = () => theme.toggleTheme()

const username = ref('')
const password = ref('')
const passwordVisible = ref(false)
const errorMsg = ref('')
const loading = ref(false)

const passwordType = computed(() => (passwordVisible.value ? 'text' : 'password'))

function clearError() {
  errorMsg.value = ''
}

async function onSubmit() {
  clearError()
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
    auth.applyAuth(res.data)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    router.push(redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/home')
  } catch (error) {
    errorMsg.value = getErrorMessage(error, '登录失败，请稍后再试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <button
      class="icon-btn auth-theme-toggle"
      type="button"
      :title="isDark ? '切换为白天模式' : '切换为夜晚模式'"
      @click="toggleTheme"
    >
      <AppIcon :name="isDark ? 'sun' : 'moon'" />
    </button>

    <aside class="auth-brand">
      <RouterLink class="brand" to="/login">
        <span class="brand-mark">
          <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <defs>
              <linearGradient
                id="hs-login-g"
                x1="0"
                y1="0"
                x2="32"
                y2="32"
                gradientUnits="userSpaceOnUse"
              >
                <stop stop-color="#5B8CFF" />
                <stop offset="0.55" stop-color="#3B6CF6" />
                <stop offset="1" stop-color="#0EB6A6" />
              </linearGradient>
            </defs>
            <rect width="32" height="32" rx="9" fill="url(#hs-login-g)" />
            <path
              d="M9.5 10.5h6.2a2 2 0 0 1 2 2v9.4a2.6 2.6 0 0 0-2.6-2.6H9.5z"
              fill="#fff"
              opacity=".95"
            />
            <path
              d="M22.5 10.5h-6.2a2 2 0 0 0-2 2v9.4a2.6 2.6 0 0 1 2.6-2.6h5.6z"
              fill="#fff"
              opacity=".68"
            />
            <circle cx="22.6" cy="9.4" r="1.5" fill="#8FF7E8" />
          </svg>
        </span>
        <span class="brand-text">
          <strong>汇书台</strong>
          <span class="brand-sub">AI Workspace</span>
        </span>
      </RouterLink>

      <h1 class="auth-title">把 AI 能力<br />做成可用的应用</h1>
      <p class="auth-subtitle">从知识库到模型服务，一个工作台完成。</p>

      <div class="auth-brand-foot">汇书台 · AI 应用落地技术整合实践</div>
    </aside>

    <section class="auth-panel">
      <div class="auth-card">
        <div class="auth-card-head">
          <h2 class="auth-card-title">登录</h2>
          <p class="auth-card-desc">使用你的账号继续。</p>
        </div>

        <form novalidate @submit.prevent="onSubmit">
          <div class="form-grid">
            <div class="field">
              <label class="field-label" for="login-username">用户名</label>
              <div class="input-icon">
                <AppIcon name="user" />
                <input
                  id="login-username"
                  v-model="username"
                  class="input"
                  placeholder="请输入用户名"
                  autocomplete="username"
                  @input="clearError"
                />
              </div>
            </div>

            <div class="field">
              <label class="field-label" for="login-password">密码</label>
              <div class="input-icon">
                <AppIcon name="lock" />
                <input
                  id="login-password"
                  v-model="password"
                  class="input"
                  :type="passwordType"
                  placeholder="请输入密码"
                  autocomplete="current-password"
                  style="padding-right: 42px"
                  @input="clearError"
                />
                <div class="input-extra">
                  <button
                    class="icon-btn"
                    type="button"
                    aria-label="显示 / 隐藏密码"
                    @click="passwordVisible = !passwordVisible"
                  >
                    <AppIcon :name="passwordVisible ? 'eye-off' : 'eye'" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <p v-if="errorMsg" class="field-error mt-3">{{ errorMsg }}</p>

          <label class="check mt-4"><input type="checkbox" checked /> 保持登录</label>

          <button class="btn btn-block btn-lg mt-4" type="submit" :disabled="loading">
            {{ loading ? '登录中…' : '登录' }}
          </button>
        </form>

        <p class="auth-switch">还没有账号？<RouterLink to="/register">注册</RouterLink></p>
      </div>
    </section>
  </div>
</template>
