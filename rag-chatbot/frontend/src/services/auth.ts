import axios from "axios"
import type { TokenResponse, User, AdminCreateUserRequest } from "@/types/user"

const BASE_URL = import.meta.env.VITE_API_URL || ""

const authApi = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
})

authApi.interceptors.request.use((config) => {
  if (config.headers.Authorization) return config
  const stored = localStorage.getItem("auth")
  if (stored) {
    try {
      const { token } = JSON.parse(stored)
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch {
    }
  }
  return config
})

authApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("auth")
      window.dispatchEvent(new CustomEvent("auth:logout"))
    }
    return Promise.reject(error)
  },
)

export async function login(email: string, password: string): Promise<TokenResponse> {
  const params = new URLSearchParams()
  params.append("username", email)
  params.append("password", password)
  const { data } = await authApi.post<TokenResponse>("/auth/token", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  })
  return data
}

export async function register(email: string, password: string): Promise<User> {
  const { data } = await authApi.post<User>("/auth/register", { email, password })
  return data
}

export async function getMe(token: string): Promise<User> {
  const { data } = await authApi.get<User>("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

export async function getUsers(): Promise<User[]> {
  const { data } = await authApi.get<User[]>("/auth/users")
  return data
}

export async function createUser(req: AdminCreateUserRequest): Promise<User> {
  const { data } = await authApi.post<User>("/auth/users", req)
  return data
}
