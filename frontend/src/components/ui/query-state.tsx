import { Alert, AlertDescription, AlertTitle } from './alert'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface QueryStateProps {
  isLoading: boolean
  isError: boolean
  error?: Error | null
  loadingMessage?: string
  errorTitle?: string
  className?: string
  children: React.ReactNode
}

/**
 * A wrapper component that handles loading and error states for data queries.
 * Shows a loading spinner while loading, an error alert if there's an error,
 * or renders children when data is ready.
 */
export function QueryState({
  isLoading,
  isError,
  error,
  loadingMessage = 'Loading...',
  errorTitle = 'Error',
  className,
  children,
}: QueryStateProps) {
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center py-8', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
        <span className="text-muted-foreground">{loadingMessage}</span>
      </div>
    )
  }

  if (isError) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertTitle>{errorTitle}</AlertTitle>
        <AlertDescription>
          {error?.message || 'An unexpected error occurred'}
        </AlertDescription>
      </Alert>
    )
  }

  return <>{children}</>
}

interface LoadingSpinnerProps {
  message?: string
  className?: string
}

/**
 * A simple loading spinner with optional message.
 */
export function LoadingSpinner({ message = 'Loading...', className }: LoadingSpinnerProps) {
  return (
    <div className={cn('flex items-center justify-center py-8', className)}>
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
      <span className="text-muted-foreground">{message}</span>
    </div>
  )
}
