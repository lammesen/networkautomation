import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { User } from '@/types'

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  activeCustomerId: number | null
}

interface AuthActions {
  setAuth: (token: string, refreshToken: string, user: User) => void
  clearAuth: () => void
  setActiveCustomer: (id: number | null) => void
}

export type AuthStore = AuthState & AuthActions

/**
 * Auth store with Zustand persist middleware
 * Uses sessionStorage to reduce persistence of tokens if XSS occurs
 */
export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      activeCustomerId: null,

      setAuth: (token, refreshToken, user) =>
        set({
          token,
          refreshToken,
          user,
          activeCustomerId: null, // Reset on login
        }),

      clearAuth: () =>
        set({
          token: null,
          refreshToken: null,
          user: null,
          activeCustomerId: null,
        }),

      setActiveCustomer: (id) => set({ activeCustomerId: id }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
        activeCustomerId: state.activeCustomerId,
      }),
    }
  )
)

// Derived selectors
export const selectIsAuthenticated = (state: AuthStore) => !!state.token
export const selectIsAdmin = (state: AuthStore) => state.user?.role === 'admin'
export const selectUser = (state: AuthStore) => state.user
export const selectToken = (state: AuthStore) => state.token
export const selectActiveCustomerId = (state: AuthStore) => state.activeCustomerId
