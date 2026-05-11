import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

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
  // 启用凭证（跨域请求时携带cookie）
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
    // 附加认证Token
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 添加请求元数据
    config.metadata = { startTime: new Date() } as any

    // 开发环境请求日志
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
 * - 统一错误处理
 * - 性能监控日志
 * - Token过期自动处理
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 性能监控：计算请求耗时
    const startTime = (response.config as any).metadata?.startTime
    if (startTime && import.meta.env.DEV) {
      const duration = Date.now() - new Date(startTime).getTime()
      if (duration > 1000) {
        console.warn(
          `[API] 慢请求警告: ${(response.config as any).method?.toUpperCase()} ${(response.config as any).url} 耗时 ${duration}ms`
        )
      }
    }

    // 直接返回data，简化调用方使用
    return response.data
  },
  (error) => {
    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response

      switch (status) {
        case 401:
          // 未授权 - 清除token并提示重新登录
          console.warn('[API] 认证失败(401)，已清除认证信息')
          localStorage.removeItem('auth_token')
          // 可以在这里触发全局登出事件
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

        default:
          console.error(`[API] HTTP错误(${status}):`, data)
      }
    } else if (error.request) {
      // 请求已发出但没有响应（网络问题）
      console.error('[API] 网络错误: 无法连接到服务器', error.message)
    } else {
      // 请求配置出错
      console.error('[API] 请求配置错误:', error.message)
    }

    return Promise.reject(error)
  }
)

// 类型导出
export type { AxiosRequestConfig, AxiosResponse }
export default apiClient
