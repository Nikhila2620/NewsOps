/**
 * Typed fetch client for the NewsOps API.
 * Adds the bearer token, converts error envelopes, and handles 401/403.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    public readonly message: string,
    public readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// Token lives in memory + sessionStorage (never localStorage — per spec)
let _token: string | null = null

export function setToken(t: string | null) {
  _token = t
  try {
    if (t) sessionStorage.setItem('newsops_token', t)
    else sessionStorage.removeItem('newsops_token')
  } catch {}
}

export function getToken(): string | null {
  if (_token) return _token
  try {
    return sessionStorage.getItem('newsops_token')
  } catch {
    return null
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  } catch {
    throw new ApiError('NETWORK_ERROR', 'Cannot reach the API', 0)
  }

  if (res.status === 401) {
    setToken(null)
    throw new ApiError('UNAUTHORIZED', 'Session expired — please log in again', 401)
  }

  if (!res.ok) {
    let code = `HTTP_${res.status}`
    let message = res.statusText
    try {
      const body = await res.json()
      // Backend error envelope: { detail: string } or { error: { code, message } }
      if (body?.error?.code) code = body.error.code
      if (body?.error?.message) message = body.error.message
      else if (typeof body?.detail === 'string') message = body.detail
    } catch {}
    throw new ApiError(code, message, res.status)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  get:    <T>(path: string)                  => request<T>(path),
  post:   <T>(path: string, body?: unknown)  => request<T>(path, { method: 'POST',  body: body !== undefined ? JSON.stringify(body) : undefined }),
  put:    <T>(path: string, body?: unknown)  => request<T>(path, { method: 'PUT',   body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch:  <T>(path: string, body?: unknown)  => request<T>(path, { method: 'PATCH', body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string)                  => request<T>(path, { method: 'DELETE' }),
}
