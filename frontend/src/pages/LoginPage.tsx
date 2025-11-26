import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient, ApiError } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function LoginPage() {
  const [isRegistering, setIsRegistering] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      if (isRegistering) {
        await apiClient.register(username, password)
        setSuccess('Registration successful! Please wait for admin approval.')
        setIsRegistering(false)
        setUsername('')
        setPassword('')
      } else {
        const data = await apiClient.login(username, password)
        const user = await apiClient.getMe(data.access_token)
        setAuth(data.access_token, data.refresh_token, user)
        navigate('/devices')
      }
    } catch (err: unknown) {
      const message = err instanceof ApiError ? err.message : (isRegistering ? 'Registration failed' : 'Login failed')
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">Network Automation</CardTitle>
          <CardDescription className="text-center">
            {isRegistering ? 'Create a new account' : 'Enter your credentials to login'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                placeholder="jdoe"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            {success && (
              <Alert className="text-green-600 border-green-200 bg-green-50">
                <AlertDescription>{success}</AlertDescription>
              </Alert>
            )}
            <Button className="w-full" type="submit" disabled={loading}>
              {loading ? 'Processing...' : (isRegistering ? 'Register' : 'Login')}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center">
          <Button
            variant="link"
            onClick={() => {
              setIsRegistering(!isRegistering)
              setError('')
              setSuccess('')
            }}
          >
            {isRegistering ? 'Already have an account? Login' : 'Need an account? Register'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}