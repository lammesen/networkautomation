import { create } from 'zustand'

interface User {
  id: number
  username: string
  role: string
  is_active: boolean
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  isAuthenticated: boolean
  setAuth: (token: string, refreshToken: string, user: User) => void
  clearAuth: () => void
}

// Simple implementation without persist middleware
const loadFromStorage = (): Partial<AuthState> => {
  try {
    const stored = localStorage.getItem('auth-storage')
    return stored ? JSON.parse(stored) : {}
  } catch {
    return {}
  }
}

const saveToStorage = (state: AuthState) => {
  try {
    localStorage.setItem('auth-storage', JSON.stringify({
      token: state.token,
      refreshToken: state.refreshToken,
      user: state.user,
      isAuthenticated: state.isAuthenticated,
    }))
  } catch {
    // Ignore storage errors
  }
}

const initialState = loadFromStorage()

export const useAuthStore = create<AuthState>((set) => ({
  token: initialState.token || null,
  refreshToken: initialState.refreshToken || null,
  user: initialState.user || null,
  isAuthenticated: initialState.isAuthenticated || false,
  setAuth: (token, refreshToken, user) => {
    const newState = { token, refreshToken, user, isAuthenticated: true }
    set(newState)
    saveToStorage({ ...newState, setAuth: () => {}, clearAuth: () => {} })
  },
  clearAuth: () => {
    const newState = { token: null, refreshToken: null, user: null, isAuthenticated: false }
    set(newState)
    saveToStorage({ ...newState, setAuth: () => {}, clearAuth: () => {} })
  },
}))
