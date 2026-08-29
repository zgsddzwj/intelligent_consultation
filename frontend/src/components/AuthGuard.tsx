import { useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { message } from 'antd'
import { getAuthUser, isAuthenticated, isTokenExpired } from '../services/auth'

interface AuthGuardProps {
  children: React.ReactNode
  requireAuth?: boolean
  allowedRoles?: string[]
}

/**
 * 路由守卫：未登录或角色不符时跳转
 * - 未登录 → 跳转登录页
 * - 已登录但角色不符 → 提示后跳回首页
 * - Token 过期 → 自动清理并跳转登录页
 * - 跨标签页同步登录状态（storage 事件监听）
 */
export default function AuthGuard({
  children,
  requireAuth = false,
  allowedRoles,
}: AuthGuardProps) {
  const location = useLocation()
  const [, setAuthVersion] = useState(0)

  // 监听跨标签页 storage 变化和自定义 logout 事件
  useEffect(() => {
    const onStorageChange = (e: StorageEvent) => {
      if (e.key === 'auth_token' || e.key === 'auth_user') {
        // 另一个标签页登录/登出 → 重新校验
        setAuthVersion((v) => v + 1)
      }
    }
    const onLogout = () => setAuthVersion((v) => v + 1)

    window.addEventListener('storage', onStorageChange)
    window.addEventListener('auth:logout', onLogout)
    return () => {
      window.removeEventListener('storage', onStorageChange)
      window.removeEventListener('auth:logout', onLogout)
    }
  }, [])

  // authVersion 变化时重新校验
  // Token 过期检查
  if (requireAuth || allowedRoles) {
    const token = localStorage.getItem('auth_token')
    if (!token || isTokenExpired()) {
      return <Navigate to="/login" state={{ from: location.pathname }} replace />
    }
  }

  // 未登录 → 跳转登录页
  if (requireAuth && !isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  // 角色权限检查
  if (allowedRoles && allowedRoles.length > 0) {
    const user = getAuthUser()
    if (!user || !allowedRoles.includes(user.role)) {
      // 未登录 → 跳转登录页
      if (!isAuthenticated()) {
        return <Navigate to="/login" state={{ from: location.pathname }} replace />
      }
      // 已登录但角色不符 → 提示并跳回首页
      return <RoleDeniedRedirect allowedRoles={allowedRoles} />
    }
  }

  return <>{children}</>
}

/** 角色不符时弹出提示并跳转首页 */
function RoleDeniedRedirect({ allowedRoles }: { allowedRoles: string[] }) {
  useEffect(() => {
    const roleLabels: Record<string, string> = {
      doctor: '医生',
      admin: '管理员',
    }
    const labels = allowedRoles.map((r) => roleLabels[r] || r).join('、')
    message.warning(`该页面需要${labels}权限，当前账号无权访问`)
  }, [allowedRoles])

  return <Navigate to="/" replace />
}
