<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import AppIcon from '@/components/ui/AppIcon.vue'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import { checkUsername, register } from '@/api/user'
import { getErrorMessage } from '@/utils/error'

const router = useRouter()
const theme = useThemeStore()
const auth = useAuthStore()

const isDark = computed(() => theme.isDark)
const toggleTheme = () => theme.toggleTheme()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const agree = ref(true)
const errorMsg = ref('')
const loading = ref(false)

const usernameState = ref('')
const usernameStateType = ref<'hint' | 'ok' | 'error' | 'loading'>('hint')
let checkSeq = 0

const runUsernameCheck = useDebounceFn(async (value: string) => {
  const seq = ++checkSeq
  try {
    const res = await checkUsername(value)
    if (seq !== checkSeq) return
    if (res.code !== 0) return
    if (res.data.available) {
      usernameState.value = '可以使用'
      usernameStateType.value = 'ok'
    } else {
      usernameState.value = '已被占用'
      usernameStateType.value = 'error'
    }
  } catch {
    if (seq === checkSeq) {
      usernameState.value = ''
      usernameStateType.value = 'hint'
    }
  }
}, 400)

function onUsernameInput() {
  usernameState.value = ''
  usernameStateType.value = 'hint'
  const value = username.value.trim()
  if (!value) return
  if (value.length < 3) {
    usernameState.value = '至少 3 位'
    usernameStateType.value = 'error'
    return
  }
  usernameState.value = '检查中…'
  usernameStateType.value = 'loading'
  void runUsernameCheck(value)
}

async function onSubmit() {
  errorMsg.value = ''
  const name = username.value.trim()
  if (!name) return (errorMsg.value = '请输入用户名')
  if (name.length < 3) return (errorMsg.value = '用户名至少 3 位')
  if (usernameStateType.value === 'error') return (errorMsg.value = '用户名不可用，请更换')
  if (password.value.length < 6) return (errorMsg.value = '密码至少 6 位')
  if (password.value !== confirmPassword.value) return (errorMsg.value = '两次输入的密码不一致')
  if (!agree.value) return (errorMsg.value = '请先同意服务条款')

  loading.value = true
  try {
    const res = await register({
      username: name,
      password: password.value,
      confirm_password: confirmPassword.value,
    })
    if (res.code !== 0) {
      errorMsg.value = res.message || '注册失败'
      return
    }
    auth.applyAuth(res.data)
    router.push('/home')
  } catch (error) {
    errorMsg.value = getErrorMessage(error, '注册失败，请稍后再试')
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
                id="hs-reg-g"
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
            <rect width="32" height="32" rx="9" fill="url(#hs-reg-g)" />
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

      <h1 class="auth-title">创建账号<br />开始使用汇书台</h1>
      <p class="auth-subtitle">注册后即可上传文档、配置模型服务。</p>

      <div class="auth-brand-foot">汇书台 · AI 应用落地技术整合实践</div>
    </aside>

    <section class="auth-panel">
      <div class="auth-card">
        <div class="auth-card-head">
          <h2 class="auth-card-title">注册</h2>
          <p class="auth-card-desc">只需用户名与密码。</p>
        </div>

        <form novalidate @submit.prevent="onSubmit">
          <div class="form-grid">
            <div class="field">
              <label class="field-label" for="reg-username">用户名</label>
              <div class="input-icon">
                <AppIcon name="user" />
                <input
                  id="reg-username"
                  v-model="username"
                  class="input"
                  placeholder="3–50 位"
                  autocomplete="username"
                  style="padding-right: 42px"
                  @input="onUsernameInput"
                />
                <div class="input-extra">
                  <span
                    class="username-state"
                    :class="{
                      'text-success': usernameStateType === 'ok',
                      'text-danger': usernameStateType === 'error',
                      subtle: usernameStateType === 'loading' || usernameStateType === 'hint',
                    }"
                  >
                    <AppIcon
                      v-if="usernameStateType === 'ok'"
                      name="circle-check"
                      class="icon-sm"
                    />
                    <AppIcon
                      v-else-if="usernameStateType === 'error'"
                      name="alert-circle"
                      class="icon-sm"
                    />
                    <span v-if="usernameState">{{ usernameState }}</span>
                  </span>
                </div>
              </div>
            </div>

            <div class="field">
              <label class="field-label" for="reg-password">密码</label>
              <div class="input-icon">
                <AppIcon name="lock" />
                <input
                  id="reg-password"
                  v-model="password"
                  class="input"
                  type="password"
                  placeholder="6–128 位"
                  autocomplete="new-password"
                />
              </div>
            </div>

            <div class="field">
              <label class="field-label" for="reg-confirm">确认密码</label>
              <div class="input-icon">
                <AppIcon name="lock" />
                <input
                  id="reg-confirm"
                  v-model="confirmPassword"
                  class="input"
                  type="password"
                  placeholder="再次输入密码"
                  autocomplete="new-password"
                />
              </div>
            </div>
          </div>

          <p v-if="errorMsg" class="field-error mt-3">{{ errorMsg }}</p>

          <label class="check mt-4">
            <input v-model="agree" type="checkbox" /> 同意《服务条款》
          </label>

          <button class="btn btn-block btn-lg mt-4" type="submit" :disabled="loading">
            {{ loading ? '创建中…' : '创建账号' }}
          </button>
        </form>

        <p class="auth-switch">已有账号？<RouterLink to="/login">登录</RouterLink></p>
      </div>
    </section>
  </div>
</template>
