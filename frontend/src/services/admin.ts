import { get, post, put, del } from './api'

// ========== 类型定义 ==========

export interface AdminUser {
  id: number
  username: string
  email: string
  role: string
  full_name: string | null
  is_active: boolean
  created_at: string | null
}

export interface UserListResponse {
  users: AdminUser[]
  total: number
  page: number
  page_size: number
}

export interface DataStats {
  users: { total: number; active: number; doctors: number; admins: number }
  consultations: { total: number; completed: number; by_agent: Record<string, number> }
  knowledge_documents: { total: number; indexed: number; unindexed: number; total_file_size_bytes: number }
  database: { size_bytes: number; size_mb: number }
}

export interface SecurityConfig {
  rbac: { enabled: boolean; roles: Record<string, string[]> }
  rate_limit: { enabled: boolean; max_calls: number; period_seconds: number; fail_closed: boolean }
  jwt: { algorithm: string; access_token_expire_minutes: number; refresh_token_expire_days: number }
  encryption: { enabled: boolean; key_configured: boolean }
  trusted_hosts: string[]
}

export interface SystemMetrics {
  uptime_seconds: number
  version: string
  environment: string
  performance: Record<string, { count: number; avg: number; min: number; max: number; latest: number; p95: number }>
  alerts: Record<string, { value: number; threshold: number; severity: string }>
  components: Record<string, { status: string; error?: string; [key: string]: any }>
}

export interface ExportRequest {
  format: 'json' | 'csv'
  sections?: string[]
}

// ========== API 服务 ==========

export const adminApi = {
  // ===== 用户管理 =====
  getUsers: (params: { page?: number; page_size?: number; role?: string; keyword?: string } = {}) =>
    get<UserListResponse>('/admin/users', { params }),

  updateUser: (userId: number, data: { role?: string; is_active?: boolean; full_name?: string }) =>
    put(`/admin/users/${userId}`, data),

  deleteUser: (userId: number) =>
    del(`/admin/users/${userId}`),

  batchActionUsers: (userIds: number[], action: 'activate' | 'deactivate' | 'delete') =>
    post('/admin/users/batch', { user_ids: userIds, action }),

  // ===== 数据管理 =====
  getDataStats: () =>
    get<DataStats>('/admin/data/stats'),

  // ===== 安全设置 =====
  getSecurityConfig: () =>
    get<SecurityConfig>('/admin/security/config'),

  // ===== 系统监控 =====
  getSystemMetrics: () =>
    get<SystemMetrics>('/admin/system/metrics'),

  // ===== 导出报告 =====
  exportReport: (data: ExportRequest) =>
    post('/admin/export', data, { responseType: 'blob' }),
}
