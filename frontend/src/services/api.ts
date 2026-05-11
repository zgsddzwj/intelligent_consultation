import axios, { AxiosError, type AxiosRequestConfig } from 'axios'

/** 后端统一响应结构 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

/** 业务错误 */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code?: number,
    public responseData?: unknown
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** 网络错误 */
export class NetworkError extends Error {
  constructor(message = '网络连接异常，请检查网络后重试') {
    super(message)
    this.name = 'NetworkError'
  }
}

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：注入 Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：统一错误处理与类型包装
api.interceptors.response.use(
  (response) => {
    // 直接返回 data，但保留 AxiosResponse 的类型推导能力
    return response.data
  },
  (error: AxiosError<ApiResponse>) => {
    if (!error.response) {
      // 无响应：网络错误或请求被取消
      return Promise.reject(new NetworkError())
    }

    const { status, data } = error.response
    const message = data?.message || error.message || '未知错误'

    switch (status) {
      case 401:
        localStorage.removeItem('auth_token')
        // 可在此触发全局登录过期事件
        window.dispatchEvent(new CustomEvent('auth:expired'))
        break
      case 403:
        console.warn('权限不足，拒绝访问')
        break
      case 429:
        console.warn('请求频率过高，请稍后重试')
        break
      case 500:
        console.error('服务器内部错误')
        break
      default:
        break
    }

    return Promise.reject(new ApiError(message, status, data?.code, data))
  }
)

/** 带类型的 GET 请求封装 */
export async function get<T = unknown>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  return api.get<unknown, T>(url, config)
}

/** 带类型的 POST 请求封装 */
export async function post<T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  return api.post<unknown, T>(url, data, config)
}

export default api
