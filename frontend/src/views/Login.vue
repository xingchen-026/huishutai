<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/user'

const router = useRouter()

const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function onSubmit() {
  errorMsg.value = ''

  // ---- 前端验证 ----
  if (!username.value.trim()) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (!password.value) {
    errorMsg.value = '请输入密码'
    return
  }
  if (password.value.length < 6) {
    errorMsg.value = '密码至少 6 位'
    return
  }

  // ---- 调后端 ----
  loading.value = true
  try {
    const res = await login(username.value.trim(), password.value)
    if (res.code === 0) {
      // 登录成功：存身份，跳首页
      localStorage.setItem('user_id', String(res.data.user_id))
      localStorage.setItem('username', res.data.username)
      router.push('/home')
    } else {
      errorMsg.value = res.message || '登录失败'
    }
  } catch (e: any) {
    // 后端返回的错误信息在 e.response.data.message
    errorMsg.value = e?.response?.data?.message || '网络错误，请稍后再试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <h2>汇书台登录</h2>

      <div class="form-item">
        <label>用户名</label>
        <input v-model="username" placeholder="请输入用户名" @keyup.enter="onSubmit" />
      </div>

      <div class="form-item">
        <label>密码</label>
        <input v-model="password" type="password" placeholder="请输入密码" @keyup.enter="onSubmit" />
      </div>

      <div v-if="errorMsg" class="error">{{ errorMsg }}</div>

      <button class="btn" :disabled="loading" @click="onSubmit">
        {{ loading ? '登录中...' : '登 录' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
}
.login-card {
  width: 340px;
  padding: 32px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
h2 {
  text-align: center;
  margin: 0 0 24px;
}
.form-item {
  margin-bottom: 16px;
}
label {
  display: block;
  font-size: 13px;
  color: #555;
  margin-bottom: 6px;
}
input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}
input:focus {
  outline: none;
  border-color: #409eff;
}
.error {
  color: #f56c6c;
  font-size: 13px;
  margin-bottom: 12px;
}
.btn {
  width: 100%;
  padding: 10px;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 15px;
  cursor: pointer;
}
.btn:disabled {
  background: #a0cfff;
  cursor: not-allowed;
}
</style>
