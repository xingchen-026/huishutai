<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { checkUsername, register } from '@/api/user'
import { setAuth } from '@/utils/auth'

const router = useRouter()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMsg = ref('')

const usernameTip = ref('')
const usernameAvailable = ref(false)
const checking = ref(false)
const loading = ref(false)

const USERNAME_RE = /^[A-Za-z0-9_\u4e00-\u9fa5]{3,50}$/

function validate() {
  const name = username.value.trim()
  if (!name) return '请输入用户名'
  if (!USERNAME_RE.test(name)) {
    return '用户名只能包含中文、字母、数字、下划线，长度 3-50 位'
  }
  if (password.value.length < 6) return '密码至少 6 位'
  if (password.value !== confirmPassword.value) return '两次输入的密码不一致'
  return ''
}

async function onCheckUsername() {
  const name = username.value.trim()
  usernameTip.value = ''
  if (!USERNAME_RE.test(name)) return

  checking.value = true
  try {
    const res = await checkUsername(name)
    if (res.code === 0) {
      usernameAvailable.value = res.data.available
      usernameTip.value = res.data.available ? '用户名可用' : '用户名已被占用'
    }
  } catch {
    // 查重失败不阻塞注册，提交时后端仍会校验
  } finally {
    checking.value = false
  }
}

async function onSubmit() {
  errorMsg.value = validate()
  if (errorMsg.value) return

  loading.value = true
  try {
    const res = await register({
      username: username.value.trim(),
      password: password.value,
      confirm_password: confirmPassword.value,
    })
    if (res.code !== 0) {
      errorMsg.value = res.message || '注册失败'
      return
    }

    setAuth(res.data.token, {
      user_id: res.data.user_id,
      username: res.data.username,
    })
    router.push('/home')
  } catch {
    errorMsg.value = '网络错误，请稍后再试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-center">
    <div class="card">
      <h2>注册汇书台</h2>
      <p class="subtitle">创建一个新账号</p>

      <form @submit.prevent="onSubmit">
        <div class="form-item">
          <label for="reg-username">用户名</label>
          <input
            id="reg-username"
            v-model="username"
            autocomplete="username"
            placeholder="3-50 位中文、字母、数字或下划线"
            @blur="onCheckUsername"
          />
          <p v-if="checking" class="form-tip">检查中...</p>
          <p v-else-if="usernameTip" class="form-tip" :class="{ 'form-tip-ok': usernameAvailable }">
            {{ usernameTip }}
          </p>
        </div>

        <div class="form-item">
          <label for="reg-password">密码</label>
          <input
            id="reg-password"
            v-model="password"
            type="password"
            autocomplete="new-password"
            placeholder="至少 6 位"
          />
        </div>

        <div class="form-item">
          <label for="reg-confirm">确认密码</label>
          <input
            id="reg-confirm"
            v-model="confirmPassword"
            type="password"
            autocomplete="new-password"
            placeholder="再次输入密码"
          />
        </div>

        <p v-if="errorMsg" class="form-error">{{ errorMsg }}</p>

        <button class="btn" type="submit" :disabled="loading">
          {{ loading ? '注册中...' : '注 册' }}
        </button>
      </form>

      <p class="switch-line">
        已有账号？
        <router-link class="link" to="/login">去登录</router-link>
      </p>
    </div>
  </div>
</template>
