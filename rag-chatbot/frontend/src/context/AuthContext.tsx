import { createContext, useEffect, useState, useCallback, type ReactNode } from "react"
import type { User, AuthState } from "@/types/user"
import { login as apiLogin, getMe } from "@/services/auth"

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

const STORAGE_KEY = "auth"

interface StoredAuth {
  token: string
  user: User
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  })

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) {
      setState((prev) => ({ ...prev, isLoading: false }))
      return
    }
    try {
      const { token } = JSON.parse(stored) as StoredAuth
      getMe(token)
        .then((fresh) => {
          setState({ user: fresh, token, isAuthenticated: true, isLoading: false })
          localStorage.setItem(STORAGE_KEY, JSON.stringify({ token, user: fresh }))
        })
        .catch(() => {
          localStorage.removeItem(STORAGE_KEY)
          setState({ user: null, token: null, isAuthenticated: false, isLoading: false })
        })
    } catch {
      localStorage.removeItem(STORAGE_KEY)
      setState((prev) => ({ ...prev, isLoading: false }))
    }
  }, [])

  useEffect(() => {
    const handleLogout = () => {
      localStorage.removeItem(STORAGE_KEY)
      setState((prev) => {
        if (!prev.isAuthenticated) return prev
        return { user: null, token: null, isAuthenticated: false, isLoading: false }
      })
    }
    window.addEventListener("auth:logout", handleLogout)
    return () => window.removeEventListener("auth:logout", handleLogout)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await apiLogin(email, password)
    const user = await getMe(access_token)
    const stored: StoredAuth = { token: access_token, user }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stored))
    setState({ user, token: access_token, isAuthenticated: true, isLoading: false })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setState({ user: null, token: null, isAuthenticated: false, isLoading: false })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
