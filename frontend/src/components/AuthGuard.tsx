import { Navigate, useLocation } from 'react-router-dom'
import { getAuthUser, isAuthenticated } from '../services/auth'

interface AuthGuardProps {
  children: React.ReactNode
  requireAuth?: boolean
  allowedRoles?: string[]
}

/**
 * 路由守卫：未登录或角色不符时跳转
 */
export default function AuthGuard({
  children,
  requireAuth = false,
  allowedRoles,
}: AuthGuardProps) {
  const location = useLocation()

  if (requireAuth && !isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const user = getAuthUser()
    if (!user || !allowedRoles.includes(user.role)) {
      if (!isAuthenticated()) {
        return <Navigate to="/login" state={{ from: location.pathname }} replace />
      }
      return <Navigate to="/" replace />
    }
  }

  return <>{children}</>
}
