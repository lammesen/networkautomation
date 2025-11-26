// Re-export from auth feature for backward compatibility
// New code should import from '@/features/auth' directly
export {
  useAuthStore,
  selectIsAuthenticated,
  selectIsAdmin,
  selectUser,
  selectToken,
  selectActiveCustomerId,
} from '@/features/auth'
export type { AuthStore } from '@/features/auth'
