/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 后端 API 地址（如 https://api.example.com），未配置时开发环境回退到本地 8000 端口 */
  readonly VITE_API_BASE_URL?: string
}
