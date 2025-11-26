export interface Customer {
  id: number
  name: string
  description?: string | null
  created_at: string
}

export interface CustomerCreate {
  name: string
  description?: string
}

export interface IPRange {
  id: number
  customer_id: number
  cidr: string
  description?: string | null
  created_at: string
}

export interface IPRangeCreate {
  cidr: string
  description?: string
}
