import { useState, useEffect, createContext, useContext } from 'react'
import { authApi } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      authApi.me()
        .then(setUser)
        .catch(() => localStorage.clear())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  async function login(email, password) {
    const data = await authApi.login({ email, password })
    localStorage.setItem('access_token',  data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    const me = await authApi.me()
    setUser(me)
    return me
  }

  async function register(payload) {
    const data = await authApi.register(payload)
    return data
  }

  async function logout() {
    try { await authApi.logout() } catch {}
    localStorage.clear()
    setUser(null)
  }

  async function refreshUser() {
    const me = await authApi.me()
    setUser(me)
    return me
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
