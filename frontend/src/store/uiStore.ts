import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'

interface UIState {
  sidebarCollapsed: boolean
  sidebarOpenSections: Set<string>
  theme: Theme
  favoriteDeviceIds: Set<number>
  recentDeviceSearches: string[]
}

interface UIActions {
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebarSection: (sectionId: string) => void
  setSidebarOpenSections: (sections: Set<string>) => void
  setTheme: (theme: Theme) => void
  toggleFavoriteDevice: (deviceId: number) => void
  isFavoriteDevice: (deviceId: number) => boolean
  addRecentSearch: (query: string) => void
  clearRecentSearches: () => void
}

export type UIStore = UIState & UIActions

const DEFAULT_OPEN_SECTIONS = ['operations', 'automation']
const MAX_RECENT_SEARCHES = 5

// Apply theme to document
function applyTheme(theme: Theme) {
  const root = window.document.documentElement
  root.classList.remove('light', 'dark')

  if (theme === 'system') {
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    root.classList.add(systemTheme)
  } else {
    root.classList.add(theme)
  }
}

export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      sidebarCollapsed: false,
      sidebarOpenSections: new Set(DEFAULT_OPEN_SECTIONS),
      theme: 'system' as Theme,
      favoriteDeviceIds: new Set<number>(),
      recentDeviceSearches: [] as string[],

      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      setSidebarCollapsed: (collapsed) =>
        set({ sidebarCollapsed: collapsed }),

      toggleSidebarSection: (sectionId) =>
        set((state) => {
          const next = new Set(state.sidebarOpenSections)
          if (next.has(sectionId)) {
            next.delete(sectionId)
          } else {
            next.add(sectionId)
          }
          return { sidebarOpenSections: next }
        }),

      setSidebarOpenSections: (sections) =>
        set({ sidebarOpenSections: sections }),

      setTheme: (theme) => {
        applyTheme(theme)
        set({ theme })
      },

      toggleFavoriteDevice: (deviceId) =>
        set((state) => {
          const next = new Set(state.favoriteDeviceIds)
          if (next.has(deviceId)) {
            next.delete(deviceId)
          } else {
            next.add(deviceId)
          }
          return { favoriteDeviceIds: next }
        }),

      isFavoriteDevice: (deviceId) => get().favoriteDeviceIds.has(deviceId),

      addRecentSearch: (query) =>
        set((state) => {
          const trimmed = query.trim()
          if (!trimmed || trimmed.length < 2) return state
          // Remove duplicates and add to front
          const filtered = state.recentDeviceSearches.filter((s) => s !== trimmed)
          return {
            recentDeviceSearches: [trimmed, ...filtered].slice(0, MAX_RECENT_SEARCHES),
          }
        }),

      clearRecentSearches: () => set({ recentDeviceSearches: [] }),
    }),
    {
      name: 'ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        // Convert Set to Array for JSON serialization
        sidebarOpenSections: Array.from(state.sidebarOpenSections),
        favoriteDeviceIds: Array.from(state.favoriteDeviceIds),
        recentDeviceSearches: state.recentDeviceSearches,
      }),
      // Convert Array back to Set on hydration
      onRehydrateStorage: () => (state) => {
        if (state) {
          if (Array.isArray(state.sidebarOpenSections)) {
            state.sidebarOpenSections = new Set(state.sidebarOpenSections as unknown as string[])
          }
          if (Array.isArray(state.favoriteDeviceIds)) {
            state.favoriteDeviceIds = new Set(state.favoriteDeviceIds as unknown as number[])
          }
          // Apply theme on hydration
          applyTheme(state.theme || 'system')
        }
      },
    }
  )
)

// Selectors
export const selectSidebarCollapsed = (state: UIStore) => state.sidebarCollapsed
export const selectSidebarOpenSections = (state: UIStore) => state.sidebarOpenSections
export const selectTheme = (state: UIStore) => state.theme
export const selectFavoriteDeviceIds = (state: UIStore) => state.favoriteDeviceIds
export const selectRecentDeviceSearches = (state: UIStore) => state.recentDeviceSearches
