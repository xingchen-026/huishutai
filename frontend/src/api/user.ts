import request from './request'

// 登录接口的返回结构（与后端 DBResult 对齐：code / message / data）
export interface LoginResult {
    code: number
    message: string
    data: { user_id: number; username: string }
}

// 登录：POST /user/login/，成功后由调用方保存身份信息到 localStorage
export function login(username: string, password: string) {
    return request.post<any, LoginResult>('/user/logion/', {username, password })
}

// 注册：POST /user/register/（预留，后续注册页可直接复用）
export function register(username: string, password: string ){
    return request.post('/user/register/', {username, password })
}