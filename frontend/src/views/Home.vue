<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { changePassword, getProfile, logout, updateProfile } from '@/api/user'
import type { Gender, UserProfile } from '@/api/user'
import { clearAuth, getAuthUser } from '@/utils/auth'

const router = useRouter()

const profile = ref<UserProfile | null>(null)
const loading = ref(true)
const pageError = ref('')

const editing = ref(false)
const saving = ref(false)
const profileMsg = ref('')
const profileError = ref('')

const form = reactive({
  email: '',
  phone: '',
  gender: 'unknown' as Gender,
})

const pwd = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})
const pwdLoading = ref(false)
const pwdMsg = ref('')
const pwdError = ref('')

const genderLabels: Record<Gender, string> = {
  male: '男',
  female: '女',
  unknown: '未知',
}

const fallbackName = getAuthUser()?.username || ''

async function loadProfile() {
  loading.value = true
  pageError.value = ''
  try {
    const res = await getProfile()
    if (res.code !== 0) {
      pageError.value = res.message || '加载用户资料失败'
      return
    }
    profile.value = res.data
    form.email = res.data.email
    form.phone = res.data.phone
    form.gender = res.data.gender
  } catch (e: any) {
    pageError.value = e?.response?.data?.message || '网络错误，请稍后再试'
  } finally {
    loading.value = false
  }
}

function startEdit() {
  if (!profile.value) return
  form.email = profile.value.email
  form.phone = profile.value.phone
  form.gender = profile.value.gender
  profileMsg.value = ''
  profileError.value = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  profileError.value = ''
}

async function saveProfile() {
  profileError.value = ''
  profileMsg.value = ''

  const email = form.email.trim()
  const phone = form.phone.trim()

  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    profileError.value = '邮箱格式不正确'
    return
  }
  if (phone && !/^1[3-9][0-9]{9}$/.test(phone)) {
    profileError.value = '手机号格式不正确'
    return
  }

  saving.value = true
  try {
    const res = await updateProfile({ email, phone, gender: form.gender })
    if (res.code !== 0) {
      profileError.value = res.message || '保存失败'
      return
    }
    profile.value = res.data
    editing.value = false
    profileMsg.value = '资料已更新'
  } catch (e: any) {
    profileError.value = e?.response?.data?.message || '网络错误，请稍后再试'
  } finally {
    saving.value = false
  }
}

async function onChangePassword() {
  pwdError.value = ''
  pwdMsg.value = ''

  if (!pwd.old_password) {
    pwdError.value = '请输入原密码'
    return
  }
  if (pwd.new_password.length < 6) {
    pwdError.value = '新密码至少 6 位'
    return
  }
  if (pwd.new_password !== pwd.confirm_password) {
    pwdError.value = '两次输入的新密码不一致'
    return
  }

  pwdLoading.value = true
  try {
    const res = await changePassword({ ...pwd })
    if (res.code !== 0) {
      pwdError.value = res.message || '修改失败'
      return
    }
    pwdMsg.value = res.message || '密码修改成功，请重新登录'
    clearAuth()
    window.setTimeout(() => router.push('/login'), 900)
  } catch (e: any) {
    pwdError.value = e?.response?.data?.message || '网络错误，请稍后再试'
  } finally {
    pwdLoading.value = false
  }
}

async function onLogout() {
  try {
    await logout()
  } catch {
    // 退出接口失败也继续清本地登录态
  }
  clearAuth()
  router.push('/login')
}

onMounted(loadProfile)
</script>

<template>
  <div class="home-page">
    <header class="home-header">
      <h1>汇书台</h1>
      <div class="home-user">
        <span>{{ profile?.username || fallbackName }}</span>
        <button class="btn btn-secondary" @click="onLogout">退出登录</button>
      </div>
    </header>

    <main class="home-main">
      <p v-if="pageError" class="form-error">{{ pageError }}</p>
      <p v-else-if="loading" class="muted">加载中...</p>

      <template v-else>
        <section class="card">
          <div class="card-head">
            <h2>个人资料</h2>
            <button v-if="!editing" class="btn btn-secondary" @click="startEdit">编辑资料</button>
          </div>

          <dl v-if="!editing" class="profile-list">
            <div>
              <dt>用户名</dt>
              <dd>{{ profile?.username }}</dd>
            </div>
            <div>
              <dt>邮箱</dt>
              <dd>{{ profile?.email || '未填写' }}</dd>
            </div>
            <div>
              <dt>手机号</dt>
              <dd>{{ profile?.phone || '未填写' }}</dd>
            </div>
            <div>
              <dt>性别</dt>
              <dd>{{ genderLabels[profile?.gender ?? 'unknown'] }}</dd>
            </div>
          </dl>

          <form v-else @submit.prevent="saveProfile">
            <div class="form-item">
              <label for="profile-email">邮箱</label>
              <input
                id="profile-email"
                v-model="form.email"
                type="email"
                placeholder="选填，例如 name@example.com"
              />
            </div>

            <div class="form-item">
              <label for="profile-phone">手机号</label>
              <input id="profile-phone" v-model="form.phone" placeholder="选填，11 位手机号" />
            </div>

            <div class="form-item">
              <label for="profile-gender">性别</label>
              <select id="profile-gender" v-model="form.gender">
                <option value="unknown">未知</option>
                <option value="male">男</option>
                <option value="female">女</option>
              </select>
            </div>

            <p v-if="profileError" class="form-error">{{ profileError }}</p>

            <div class="btn-row">
              <button class="btn" type="submit" :disabled="saving">
                {{ saving ? '保存中...' : '保存' }}
              </button>
              <button class="btn btn-secondary" type="button" @click="cancelEdit">取消</button>
            </div>
          </form>

          <p v-if="profileMsg" class="form-success">{{ profileMsg }}</p>
        </section>

        <section class="card">
          <h2>修改密码</h2>

          <form @submit.prevent="onChangePassword">
            <div class="form-item">
              <label for="pwd-old">原密码</label>
              <input
                id="pwd-old"
                v-model="pwd.old_password"
                type="password"
                autocomplete="current-password"
              />
            </div>

            <div class="form-item">
              <label for="pwd-new">新密码</label>
              <input
                id="pwd-new"
                v-model="pwd.new_password"
                type="password"
                autocomplete="new-password"
                placeholder="至少 6 位"
              />
            </div>

            <div class="form-item">
              <label for="pwd-confirm">确认新密码</label>
              <input
                id="pwd-confirm"
                v-model="pwd.confirm_password"
                type="password"
                autocomplete="new-password"
              />
            </div>

            <p v-if="pwdError" class="form-error">{{ pwdError }}</p>
            <p v-if="pwdMsg" class="form-success">{{ pwdMsg }}</p>

            <button class="btn" type="submit" :disabled="pwdLoading">
              {{ pwdLoading ? '提交中...' : '修改密码' }}
            </button>
          </form>
        </section>
      </template>
    </main>
  </div>
</template>
