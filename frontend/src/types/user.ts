export interface User {
  id: number
  username: string
  role: 'admin' | 'operator' | 'viewer'
  is_active: boolean
  created_at?: string
  updated_at?: string
  customers?: { id: number; name: string }[]
}

export interface UserCreate {
  username: string
  password: string
}

export interface AdminUserCreate {
  username: string
  password: string
  role: 'admin' | 'operator' | 'viewer'
  is_active: boolean
  customer_ids: number[]
}

export interface UserUpdate {
  role?: string
  is_active?: boolean
}
