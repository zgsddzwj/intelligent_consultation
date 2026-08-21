import { post } from './api'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user_id: number
  username: string
  role: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  role?: string
}

/** JWT Token 过期检查阈值（秒），提前 5 分钟判定即将过期 */
const TOKEN_EXPIRY_THRESHOLD = 5 * 60

export const authApi = {
  login: (data: LoginRequest) => post<LoginResponse>('/users/login', data),

  register: (data: RegisterRequest) => post('/users/register', data),
}

export function saveAuthToken(token: string, user?: { id: number; username: string; role: string }) {
  localStorage.setItem('auth_token', token)
  if (user) {
    localStorage.setItem('auth_user', JSON.stringify(user))
  }
  // 记录保存时间，用于粗略判断 token 新鲜度
  localStorage.setItem('auth_token_saved_at', String(Date.now()))
}

export function clearAuthToken() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_user')
  localStorage.removeItem('auth_token_saved_at')
}

export function getAuthUser(): { id: number; username: string; role: string } | null {
  const raw = localStorage.getItem('auth_user')
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    // JSON 解析失败时自动清理脏数据
    clearAuthToken()
    return null
  }
}

/**
 * 解析 JWT payload 部分（不验证签名，仅客户端预判过期）
 * 返回 null 表示无法解析
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    // atob 兼容 base64url：补齐 padding 并替换字符
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4)
    const json = decodeURIComponent(
      atob(padded)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(json)
  } catch {
    return null
  }
}

/**
 * 检查 Token 是否已过期或即将过期
 * - 如果 token 无法解析或已过期 → true
 * - 如果 token 在阈值内即将过期 → true
 */
export function isTokenExpired(): boolean {
  const token = localStorage.getItem('auth_token')
  if (!token) return true

  const payload = decodeJwtPayload(token)
  if (!payload) return true

  const exp = payload['exp'] as number | undefined
  if (!exp) return false // 无 exp 字段时不做判断

  const now = Math.floor(Date.now() / 1000)
  return now + TOKEN_EXPIRY_THRESHOLD >= exp
}

export function isAuthenticated(): boolean {
  const token = localStorage.getItem('auth_token')
  if (!token) return false

  // Token 过期时自动清理
  if (isTokenExpired()) {
    clearAuthToken()
    window.dispatchEvent(new CustomEvent('auth:logout'))
    return false
  }

  return true
}
