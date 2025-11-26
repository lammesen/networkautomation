/**
 * MSW server setup for Node.js/Bun test environment
 */
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

/**
 * MSW server instance with default handlers
 */
export const server = setupServer(...handlers)

/**
 * Setup function to be called in test setup
 */
export function setupMswServer() {
  // Start server before all tests
  beforeAll(() => {
    server.listen({ onUnhandledRequest: 'warn' })
  })

  // Reset handlers after each test
  afterEach(() => {
    server.resetHandlers()
  })

  // Close server after all tests
  afterAll(() => {
    server.close()
  })

  return server
}
