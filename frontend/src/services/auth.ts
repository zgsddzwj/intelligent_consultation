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

export const authApi = {
  login: (data: LoginRequest) => post<LoginResponse>('/users/login', data),

  register: (data: RegisterRequest) => post('/users/register', data),
}

export function saveAuthToken(token: string, user?: { id: number; username: string; role: string }) {
  localStorage.setItem('auth_token', token)
  if (user) {
    localStorage.setItem('auth_user', JSON.stringify(user))
  }
}

export function clearAuthToken() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_user')
}

export function getAuthUser(): { id: number; username: string; role: string } | null {
  const raw = localStorage.getItem('auth_user')
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem('auth_token')
}
