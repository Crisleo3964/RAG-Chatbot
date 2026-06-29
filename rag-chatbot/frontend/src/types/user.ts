export interface User {
  user_id: string
  email: string
  role: "admin" | "user"
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface RegisterRequest {
  email: string
  password: string
}

export interface AdminCreateUserRequest {
  email: string
  password: string
  role?: "user" | "admin"
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}
