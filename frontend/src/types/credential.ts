export interface Credential {
  id: number
  customer_id: number
  name: string
  username: string
  created_at: string
}

export interface CredentialCreate {
  name: string
  username: string
  password: string
  enable_password?: string
}

export interface CredentialUpdate {
  name?: string
  username?: string
  password?: string
  enable_password?: string
}
