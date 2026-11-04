import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { AuthData } from '@/api/user'
import { clearAuth, getAuthUser, getToken, setAuth, type AuthUser } from '@/utils/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref<AuthUser | null>(getAuthUser())

  const isLoggedIn = computed(() => Boolean(token.value))
  const username = computed(() => user.value?.username || '')
  const userId = computed(() => user.value?.user_id ?? null)
  const avatarText = computed(() => (username.value || '?').slice(0, 1).toUpperCase())

  function applyAuth(data: AuthData) {
    const nextUser: AuthUser = { user_id: data.user_id, username: data.username }
    setAuth(data.token, nextUser)
    token.value = data.token
    user.value = nextUser
  }

  function clear() {
    clearAuth()
    token.value = ''
    user.value = null
  }

  return { token, user, isLoggedIn, username, userId, avatarText, applyAuth, clear }
})
