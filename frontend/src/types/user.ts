export interface User {
  id: number
  username: string
  role: 'admin' | 'operator' | 'viewer'
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface UserCreate {
  username: string
  password: string
}

export interface UserUpdate {
  role?: string
  is_active?: boolean
}
