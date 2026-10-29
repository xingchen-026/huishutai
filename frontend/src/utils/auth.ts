export interface AuthUser {
  user_id: number
  username: string
}

const TOKEN_KEY = 'access_token'
const USER_KEY = 'auth_user'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getAuthUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

export function setAuth(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  // 清理旧版本留下的字段
  localStorage.removeItem('user_id')
  localStorage.removeItem('username')
}

export function isLoggedIn(): boolean {
  return Boolean(getToken())
}
