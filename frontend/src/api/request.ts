import axios from 'axios'

const request = axios.create({
    baseURL: '/api',    //配合vite代理
    timeout: 10000,
})

// 响应拦截：直接把后端的 {code, message, data} 透出来
request.interceptors.response.use(
    (res) => res.data,
    (err) => Promise.reject(err),
)

export default request