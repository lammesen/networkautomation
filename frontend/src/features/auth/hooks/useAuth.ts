import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { useAuthStore } from '../store'

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation({
    mutationFn: async ({ username, password }: { username: string; password: string }) => {
      const response = await apiClient.login(username, password)
      // Fetch user info
      const user = await apiClient.getMe(response.access_token)
      return { ...response, user }
    },
    onSuccess: (data) => {
      setAuth(data.access_token, data.refresh_token, data.user)
    },
  })
}

export function useLogout() {
  const clearAuth = useAuthStore((s) => s.clearAuth)

  return () => {
    clearAuth()
  }
}

export function useRegister() {
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      apiClient.register(username, password),
  })
}
