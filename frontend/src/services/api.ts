import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    metadata?: { startTime: Date }
  }
}

/**
 * API响应统一格式
 */
export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message?: string
  error?: {
    code: string
    message: string
    details?: Record<string, any>
    request_id?: string
  }
}

/**
 * API错误类型
 */
export class ApiError extends Error {
  status: number
  code: string
  requestId?: string
  details?: Record<string, any>

  constructor(status: number, code: string, message: string, requestId?: string, details?: Record<string, any>) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.details = details
  }
}

/**
 * API客户端配置
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
  withCredentials: false,
})

/**
 * 请求拦截器
 * - 自动附加认证Token
 * - 添加请求时间戳用于性能监控
 * - 请求日志（开发环境）
 */
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    config.metadata = { startTime: new Date() }

    if (import.meta.env.DEV) {
      console.log(
        `%c[API] ${config.method?.toUpperCase()} ${config.url}`,
        'color: #667eea; font-weight: 600;',
        config.data || '(无请求体)'
      )
    }

    return config
  },
  (error) => {
    console.error('[API] 请求错误:', error)
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 * - 统一错误处理与ApiError转换
 * - 性能监控日志
 * - Token过期自动处理
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const startTime = response.config.metadata?.startTime
    if (startTime && import.meta.env.DEV) {
      const duration = Date.now() - new Date(startTime).getTime()
      if (duration > 1000) {
        console.warn(
          `[API] 慢请求警告: ${(response.config as any).method?.toUpperCase()} ${(response.config as any).url} 耗时 ${duration}ms`
        )
      }
    }

    // 如果后端返回统一格式，提取data
    const data = response.data
    if (data && typeof data === 'object' && 'success' in data) {
      if (!data.success) {
        return Promise.reject(
          new ApiError(
            response.status,
            data.error?.code || 'UNKNOWN_ERROR',
            data.error?.message || '请求失败',
            data.error?.request_id,
            data.error?.details
          )
        )
      }
      return data.data
    }

    return data
  },
  (error: AxiosError<ApiResponse>) => {
    if (error.response) {
      const { status, data } = error.response

      const apiError = new ApiError(
        status,
        data?.error?.code || `HTTP_${status}`,
        data?.error?.message || error.message,
        data?.error?.request_id,
        data?.error?.details
      )

      switch (status) {
        case 401:
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_user')
          if (!window.location.pathname.startsWith('/login')) {
            window.location.href = '/login'
          }
          window.dispatchEvent(new CustomEvent('auth:logout', { detail: { reason: 'token_expired' } }))
          break
        case 403:
          console.error('[API] 权限不足(403)')
          break
        case 404:
          console.warn('[API] 资源不存在(404):', error.request?.responseURL)
          break
        case 429:
          console.warn('[API] 请求频率过高(429)，请稍后重试')
          break
        case 500:
        case 502:
        case 503:
        case 504:
          console.error(`[API] 服务器错误(${status})`)
          break
      }

      return Promise.reject(apiError)
    } else if (error.request) {
      const networkError = new ApiError(0, 'NETWORK_ERROR', '网络错误: 无法连接到服务器')
      return Promise.reject(networkError)
    } else {
      const configError = new ApiError(0, 'CONFIG_ERROR', error.message)
      return Promise.reject(configError)
    }
  }
)

// ===== 便捷请求方法 =====

export function get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.get(url, config)
}

export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.post(url, data, config)
}

export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.put(url, data, config)
}

export function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.delete(url, config)
}

export function patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.patch(url, data, config)
}

// 类型导出
export type { AxiosRequestConfig, AxiosResponse }
export default apiClient
