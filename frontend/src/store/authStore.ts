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
  activeCustomerId: number | null
  setAuth: (token: string, refreshToken: string, user: User) => void
  clearAuth: () => void
  setActiveCustomer: (id: number | null) => void
}

// Simple implementation without persist middleware
// switched to sessionStorage to reduce persistence of tokens if XSS occurs
const loadFromStorage = (): Partial<AuthState> => {
  try {
    const stored = sessionStorage.getItem('auth-storage')
    return stored ? JSON.parse(stored) : {}
  } catch {
    return {}
  }
}

const saveToStorage = (state: AuthState) => {
  try {
    sessionStorage.setItem('auth-storage', JSON.stringify({
      token: state.token,
      refreshToken: state.refreshToken,
      user: state.user,
      isAuthenticated: state.isAuthenticated,
      activeCustomerId: state.activeCustomerId,
    }))
  } catch {
    // Ignore storage errors
  }
}

const initialState = loadFromStorage()

export const useAuthStore = create<AuthState>((set) => ({
// ... (keep rest of file)
  token: initialState.token || null,
  refreshToken: initialState.refreshToken || null,
  user: initialState.user || null,
  isAuthenticated: initialState.isAuthenticated || false,
  activeCustomerId: initialState.activeCustomerId || null,
  setAuth: (token, refreshToken, user) => {
    const newState = { 
      token, 
      refreshToken, 
      user, 
      isAuthenticated: true,
      activeCustomerId: null // Reset on login? Or keep? Better reset or default logic elsewhere.
    }
    set(newState)
    saveToStorage({ ...newState, setAuth: () => {}, clearAuth: () => {}, setActiveCustomer: () => {} })
  },
  clearAuth: () => {
    const newState = { 
      token: null, 
      refreshToken: null, 
      user: null, 
      isAuthenticated: false,
      activeCustomerId: null
    }
    set(newState)
    saveToStorage({ ...newState, setAuth: () => {}, clearAuth: () => {}, setActiveCustomer: () => {} })
  },
  setActiveCustomer: (id) => {
    set((state) => {
      const newState = { ...state, activeCustomerId: id }
      saveToStorage(newState)
      return newState
    })
  }
}))
