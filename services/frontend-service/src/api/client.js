const BASE = '/api'

function getToken() {
  return localStorage.getItem('access_token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  // Auto-refresh on 401
  if (res.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      headers.Authorization = `Bearer ${getToken()}`
      const retry = await fetch(`${BASE}${path}`, { ...options, headers })
      if (!retry.ok) throw await retry.json()
      return retry.status === 204 ? null : retry.json()
    }
    // Refresh failed — clear auth and redirect
    localStorage.clear()
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw err
  }

  return res.status === 204 ? null : res.json()
}

async function tryRefresh() {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return false
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!res.ok) return false
    const data = await res.json()
    localStorage.setItem('access_token', data.access_token)
    return true
  } catch {
    return false
  }
}

export const api = {
  get:    (path, opts)   => request(path, { method: 'GET', ...opts }),
  post:   (path, body)   => request(path, { method: 'POST',   body: JSON.stringify(body) }),
  patch:  (path, body)   => request(path, { method: 'PATCH',  body: JSON.stringify(body) }),
  delete: (path)         => request(path, { method: 'DELETE' }),
}
