import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError, AxiosInterceptorManager, InternalAxiosRequestConfig } from 'axios'

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    metadata?: { startTime: Date }
    _retryCount?: number
    _isRetryable?: boolean
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
  isRetryable: boolean

  constructor(
    status: number,
    code: string,
    message: string,
    requestId?: string,
    details?: Record<string, any>,
    isRetryable: boolean = false
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.details = details
    this.isRetryable = isRetryable
  }
}

// ===== 超时分级配置 =====
const TIMEOUT_PRESETS = {
  fast: 10000,       // 快速请求（GET、DELETE）：10秒
  normal: 30000,     // 普通请求（POST、PUT）：30秒
  slow: 60000,       // 慢请求（AI聊天、文件上传）：60秒
} as const

// ===== 重试配置 =====
const MAX_RETRY_COUNT = 2
const RETRY_DELAY_BASE = 1000 // 1秒基数，指数退避
const RETRYABLE_STATUS = new Set([408, 429, 500, 502, 503, 504])

// ===== 在线状态检测 =====
let isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    isOnline = true
    console.info('[API] 网络已恢复')
  })
  window.addEventListener('offline', () => {
    isOnline = false
    console.warn('[API] 网络已断开')
  })
}

/**
 * 根据请求方法自动选择超时时长
 */
function getTimeoutForRequest(config: AxiosRequestConfig): number {
  // 显式指定的超时优先
  if (config.timeout) return config.timeout

  // AI聊天和文件上传路径使用慢超时
  const url = config.url || ''
  if (url.includes('/consultation/chat') || url.includes('/image') || url.includes('/upload')) {
    return TIMEOUT_PRESETS.slow
  }

  const method = (config.method || 'get').toLowerCase()
  if (method === 'get' || method === 'delete') {
    return TIMEOUT_PRESETS.fast
  }
  return TIMEOUT_PRESETS.normal
}

/**
 * 延迟函数（指数退避）
 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * API客户端配置
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
  withCredentials: false,
})

/**
 * 请求拦截器
 * - 自动附加认证Token
 * - 离线检测
 * - 自动设置超时分级
 * - 添加请求时间戳用于性能监控
 * - 请求日志（开发环境）
 */
apiClient.interceptors.request.use(
  (config) => {
    // 离线检测
    if (!isOnline) {
      return Promise.reject(
        new ApiError(0, 'OFFLINE', '网络已断开，请检查网络连接后重试', undefined, undefined, false)
      )
    }

    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 自动设置超时
    if (!config.timeout) {
      config.timeout = getTimeoutForRequest(config)
    }

    config.metadata = { startTime: new Date() }
    config._retryCount = config._retryCount || 0

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
 * - 自动重试（网络错误和5xx）
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
            data.error?.details,
            false
          )
        )
      }
      return data.data
    }

    return data
  },
  async (error: AxiosError<ApiResponse>) => {
    const config = error.config as InternalAxiosRequestConfig | undefined

    // ===== 自动重试逻辑 =====
    if (config && shouldRetry(error, config)) {
      const retryCount = config._retryCount || 0
      if (retryCount < MAX_RETRY_COUNT) {
        config._retryCount = retryCount + 1
        const delayMs = RETRY_DELAY_BASE * Math.pow(2, retryCount)
        if (import.meta.env.DEV) {
          console.warn(`[API] 自动重试 (${retryCount + 1}/${MAX_RETRY_COUNT}) ${config.url}，${delayMs}ms后重试`)
        }
        await delay(delayMs)
        return apiClient.request(config)
      }
    }

    if (error.response) {
      const { status, data } = error.response
      const isRetryable = RETRYABLE_STATUS.has(status)

      const apiError = new ApiError(
        status,
        data?.error?.code || `HTTP_${status}`,
        data?.error?.message || error.message,
        data?.error?.request_id,
        data?.error?.details,
        isRetryable
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
      // 网络错误（已重试过或不可重试）
      const message = !isOnline ? '网络已断开，请检查网络连接' : '网络错误: 无法连接到服务器'
      const networkError = new ApiError(0, 'NETWORK_ERROR', message, undefined, undefined, false)
      return Promise.reject(networkError)
    } else {
      const configError = new ApiError(0, 'CONFIG_ERROR', error.message)
      return Promise.reject(configError)
    }
  }
)

/**
 * 判断是否应该重试
 */
function shouldRetry(error: AxiosError, config: InternalAxiosRequestConfig): boolean {
  // 已经达到最大重试次数
  if ((config._retryCount || 0) >= MAX_RETRY_COUNT) return false

  // 非GET请求不自动重试（避免重复写操作），除非显式标记可重试
  const method = (config.method || 'get').toLowerCase()
  if (method !== 'get' && !config._isRetryable) return false

  // 网络错误（无响应）可重试
  if (!error.response) return true

  // 特定HTTP状态码可重试
  return RETRYABLE_STATUS.has(error.response.status)
}

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

// ===== 工具函数导出 =====

/** 检查当前是否在线 */
export function checkOnline(): boolean {
  return isOnline
}

/** 创建可取消的请求（基于AbortController） */
export function createCancellableRequest(): {
  signal: AbortSignal
  cancel: () => void
} {
  const controller = new AbortController()
  return {
    signal: controller.signal,
    cancel: () => controller.abort(),
  }
}

// 类型导出
export type { AxiosRequestConfig, AxiosResponse }
export default apiClient
