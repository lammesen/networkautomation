import React, { PropsWithChildren } from 'react'
import { render, RenderOptions, RenderResult } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

/**
 * Create a fresh QueryClient for each test to avoid cache pollution
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

interface TestProviderProps extends PropsWithChildren {
  queryClient?: QueryClient
}

/**
 * Wrapper component with all providers needed for testing
 */
export function TestProviders({ children, queryClient }: TestProviderProps) {
  const client = queryClient ?? createTestQueryClient()

  return (
    <QueryClientProvider client={client}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient
}

/**
 * Custom render function that wraps components with test providers
 */
export function renderWithProviders(
  ui: React.ReactElement,
  options: CustomRenderOptions = {}
): RenderResult & { queryClient: QueryClient } {
  const { queryClient = createTestQueryClient(), ...renderOptions } = options

  const Wrapper = ({ children }: PropsWithChildren) => (
    <TestProviders queryClient={queryClient}>{children}</TestProviders>
  )

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  }
}

/**
 * Wait for async operations to complete
 */
export async function waitForLoadingToFinish(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

// Re-export everything from testing-library
export * from '@testing-library/react'
export { renderWithProviders as render }

// Re-export MSW utilities
export { server, setupMswServer } from './mocks/server'
export { handlers, errorHandlers } from './mocks/handlers'

// Re-export mock factories
export * from './mocks/factories'
