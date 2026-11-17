const configuredApiUrl = import.meta.env.VITE_API_URL?.trim()

export const API_URL = (configuredApiUrl || 'http://127.0.0.1:8000').replace(/\/+$/, '')
export const AUTH_TOKEN_KEY = 'insightflow_access_token'
export const AUTH_USER_KEY = 'insightflow_authenticated_user'

export interface AuthUser {
  id: string
  email: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
  user: AuthUser
}

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = sessionStorage.getItem(AUTH_TOKEN_KEY)
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(input, { ...init, headers })
  const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
  if (response.status === 401 && !url.includes('/api/v1/auth/login') && !url.includes('/api/v1/auth/register')) {
    sessionStorage.removeItem(AUTH_TOKEN_KEY)
    sessionStorage.removeItem(AUTH_USER_KEY)
    window.dispatchEvent(new Event('insightflow:unauthorized'))
  }
  return response
}
