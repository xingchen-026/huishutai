<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/ui/AppIcon.vue'
import { useToastStore } from '@/stores/toast'
import { useAuthStore } from '@/stores/auth'
import { changePassword, getProfile, updateProfile } from '@/api/user'
import type { Gender, UserProfile } from '@/api/user'
import { clearAuth } from '@/utils/auth'
import { getErrorMessage } from '@/utils/error'

const router = useRouter()
const toast = useToastStore()
const auth = useAuthStore()

const GENDER_LABELS: Record<Gender, string> = { male: '男', female: '女', unknown: '未知' }

const profile = ref<UserProfile | null>(null)
const loading = ref(true)
const pageError = ref('')
const passwordCard = ref<HTMLElement | null>(null)

const editing = ref(false)
const saving = ref(false)
const formError = ref('')
const form = reactive<{ email: string; phone: string; gender: Gender }>({
  email: '',
  phone: '',
  gender: 'unknown',
})

const pwd = reactive({ old_password: '', new_password: '', confirm_password: '' })
const pwdLoading = ref(false)
const pwdError = ref('')

const displayName = computed(() => profile.value?.username || auth.username || '未登录')
const avatarText = computed(() => displayName.value.slice(0, 1).toUpperCase())

async function loadProfile() {
  loading.value = true
  pageError.value = ''
  try {
    const res = await getProfile()
    if (res.code !== 0) throw new Error(res.message)
    profile.value = res.data
    form.email = res.data.email
    form.phone = res.data.phone
    form.gender = res.data.gender
  } catch (err) {
    pageError.value = getErrorMessage(err, '加载用户资料失败')
  } finally {
    loading.value = false
  }
}

function enterEdit() {
  if (!profile.value) return
  form.email = profile.value.email
  form.phone = profile.value.phone
  form.gender = profile.value.gender
  formError.value = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  formError.value = ''
}

async function saveProfile() {
  formError.value = ''
  const email = form.email.trim()
  const phone = form.phone.trim()
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    formError.value = '邮箱格式不正确'
    return
  }
  if (phone && !/^1[3-9]\d{9}$/.test(phone)) {
    formError.value = '手机号格式不正确'
    return
  }

  saving.value = true
  try {
    const res = await updateProfile({ email, phone, gender: form.gender })
    if (res.code !== 0) throw new Error(res.message)
    profile.value = res.data
    editing.value = false
    toast.success('资料已更新')
  } catch (err) {
    formError.value = getErrorMessage(err, '保存失败，请稍后再试')
  } finally {
    saving.value = false
  }
}

function scrollToPassword() {
  passwordCard.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

async function onSubmitPassword() {
  pwdError.value = ''
  if (!pwd.old_password) return (pwdError.value = '请输入原密码')
  if (pwd.new_password.length < 6) return (pwdError.value = '新密码至少 6 位')
  if (pwd.new_password !== pwd.confirm_password) return (pwdError.value = '两次输入的新密码不一致')

  pwdLoading.value = true
  try {
    const res = await changePassword({ ...pwd })
    if (res.code !== 0) throw new Error(res.message)
    toast.success('密码修改成功', '请重新登录')
    clearAuth()
    auth.clear()
    window.setTimeout(() => router.push('/login'), 900)
  } catch (err) {
    pwdError.value = getErrorMessage(err, '修改失败，请稍后再试')
  } finally {
    pwdLoading.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <div class="page-head">
    <div class="page-head-main">
      <h1 class="page-title">个人中心</h1>
      <p class="page-desc">管理账号资料与密码。</p>
    </div>
    <div class="page-actions">
      <button class="btn btn-secondary" type="button" @click="scrollToPassword">修改密码</button>
      <button class="btn btn-primary" type="button" @click="editing ? cancelEdit() : enterEdit()">
        <AppIcon name="edit" />{{ editing ? '取消编辑' : '编辑资料' }}
      </button>
    </div>
  </div>

  <p v-if="pageError" class="field-error mb-3">{{ pageError }}</p>
  <p v-else-if="loading" class="muted mb-3">加载中…</p>

  <div class="split">
    <section class="card identity-card">
      <span class="avatar avatar-lg identity-avatar">{{ avatarText }}</span>
      <div class="identity-name">{{ displayName }}</div>
      <div class="identity-handle">@{{ profile?.username || auth.username }}</div>
      <div class="identity-foot">签名 Token · 7 天有效</div>
    </section>

    <div class="col" style="gap: 18px">
      <section class="card">
        <div class="card-head">
          <div class="card-head-main"><h3 class="card-title">个人资料</h3></div>
          <div class="card-extra">
            <span class="badge" :class="editing ? 'badge-info' : 'badge-dashed'">
              {{ editing ? '编辑' : '查看' }}
            </span>
          </div>
        </div>

        <div v-if="!editing" class="card-body profile-view">
          <dl class="kv">
            <dt>用户名</dt>
            <dd class="mono">{{ profile?.username }}</dd>
            <dt>邮箱</dt>
            <dd>{{ profile?.email || '未填写' }}</dd>
            <dt>手机号</dt>
            <dd>{{ profile?.phone || '未填写' }}</dd>
            <dt>性别</dt>
            <dd>{{ GENDER_LABELS[profile?.gender || 'unknown'] }}</dd>
          </dl>
        </div>

        <div v-else class="card-body">
          <form novalidate @submit.prevent="saveProfile">
            <div class="form-grid">
              <div class="field">
                <label class="field-label" for="profile-email">邮箱</label>
                <input
                  id="profile-email"
                  v-model="form.email"
                  class="input"
                  type="email"
                  placeholder="选填"
                />
              </div>
              <div class="field">
                <label class="field-label" for="profile-phone">手机号</label>
                <input
                  id="profile-phone"
                  v-model="form.phone"
                  class="input"
                  placeholder="选填，11 位手机号"
                />
              </div>
              <div class="field">
                <label class="field-label" for="profile-gender">性别</label>
                <div class="select-wrap">
                  <select id="profile-gender" v-model="form.gender" class="select">
                    <option value="unknown">未知</option>
                    <option value="male">男</option>
                    <option value="female">女</option>
                  </select>
                </div>
              </div>
            </div>
            <p v-if="formError" class="field-error mt-3">{{ formError }}</p>
            <div class="form-actions mt-4">
              <button class="btn" type="submit" :disabled="saving">
                {{ saving ? '保存中…' : '保存' }}
              </button>
              <button class="btn btn-secondary" type="button" @click="cancelEdit">取消</button>
            </div>
          </form>
        </div>
      </section>

      <section id="password-card" ref="passwordCard" class="card">
        <div class="card-head">
          <div class="card-head-main"><h3 class="card-title">修改密码</h3></div>
          <div class="card-extra"><span class="fs-xs subtle">修改后需重新登录</span></div>
        </div>
        <div class="card-body">
          <form novalidate @submit.prevent="onSubmitPassword">
            <div class="form-grid">
              <div class="field">
                <label class="field-label" for="old-password">原密码</label>
                <input
                  id="old-password"
                  v-model="pwd.old_password"
                  class="input"
                  type="password"
                  autocomplete="current-password"
                />
              </div>
              <div class="field">
                <label class="field-label" for="new-password">新密码</label>
                <input
                  id="new-password"
                  v-model="pwd.new_password"
                  class="input"
                  type="password"
                  placeholder="6–128 位"
                  autocomplete="new-password"
                />
              </div>
              <div class="field">
                <label class="field-label" for="confirm-password">确认新密码</label>
                <input
                  id="confirm-password"
                  v-model="pwd.confirm_password"
                  class="input"
                  type="password"
                  autocomplete="new-password"
                />
              </div>
            </div>
            <p v-if="pwdError" class="field-error mt-3">{{ pwdError }}</p>
            <div class="form-actions mt-4">
              <button class="btn" type="submit" :disabled="pwdLoading">
                {{ pwdLoading ? '提交中…' : '修改密码' }}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  </div>
</template>
