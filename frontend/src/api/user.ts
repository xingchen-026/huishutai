import request from "./request"

// 后端统一返回结构：{ code, message, data }
export interface ApiResult<T = unknown> {
    code: number
    message: string
    data: T
}

export interface AuthData {
    token: string
    user_id: number
    username: string
}

export type Gender = 'male' | 'female' | 'unknown'

export interface UserProfile {
  user_id: number
  username: string
  email: string
  phone: string
  gender: Gender
}

export interface RegisterPayload {
  username: string
  password: string
  confirm_password: string
}

// 登录：POST /user/login/
export function login(username: string, password: string) {
  return request.post<any, ApiResult<AuthData>>('/user/login/', { username, password })
}

// 注册：POST /user/register/，成功后后端直接返回 token
export function register(payload: RegisterPayload) {
  return request.post<any, ApiResult<AuthData>>('/user/register/', payload)
}

// 用户名查重：GET /user/check-username/?username=xxx
export function checkUsername(username: string) {
  return request.get<any, ApiResult<{ username: string; available: boolean }>>(
    '/user/check-username/',
    { params: { username } },
  )
}

// 当前登录用户资料：GET /user/info/
export function getProfile() {
  return request.get<any, ApiResult<UserProfile>>('/user/info/')
}

// 更新资料：PATCH /user/info/
export function updateProfile(
  payload: Partial<Pick<UserProfile, 'email' | 'phone' | 'gender'>>,
) {
  return request.patch<any, ApiResult<UserProfile>>('/user/info/', payload)
}

// 修改密码：POST /user/password/
export function changePassword(payload: {
  old_password: string
  new_password: string
  confirm_password: string
}) {
  return request.post<any, ApiResult<null>>('/user/password/', payload)
}

// 退出：POST /user/logout/（服务端无状态，主要靠前端清 token）
export function logout() {
  return request.post<any, ApiResult<null>>('/user/logout/')
}