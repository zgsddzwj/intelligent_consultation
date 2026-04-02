import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    // 处理常见错误
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // 未授权，清除token
          localStorage.removeItem('auth_token')
          break
        case 429:
          // 限流错误
          console.warn('请求频率过高，请稍后重试')
          break
        case 500:
          // 服务器错误
          console.error('服务器内部错误')
          break
      }
    }
    return Promise.reject(error)
  }
)

export default api

