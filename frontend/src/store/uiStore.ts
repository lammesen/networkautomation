import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface UIState {
  sidebarCollapsed: boolean
  sidebarOpenSections: Set<string>
}

interface UIActions {
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebarSection: (sectionId: string) => void
  setSidebarOpenSections: (sections: Set<string>) => void
}

export type UIStore = UIState & UIActions

const DEFAULT_OPEN_SECTIONS = ['operations', 'automation']

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      sidebarOpenSections: new Set(DEFAULT_OPEN_SECTIONS),

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
    }),
    {
      name: 'ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        // Convert Set to Array for JSON serialization
        sidebarOpenSections: Array.from(state.sidebarOpenSections),
      }),
      // Convert Array back to Set on hydration
      onRehydrateStorage: () => (state) => {
        if (state && Array.isArray(state.sidebarOpenSections)) {
          state.sidebarOpenSections = new Set(state.sidebarOpenSections as unknown as string[])
        }
      },
    }
  )
)

// Selectors
export const selectSidebarCollapsed = (state: UIStore) => state.sidebarCollapsed
export const selectSidebarOpenSections = (state: UIStore) => state.sidebarOpenSections
