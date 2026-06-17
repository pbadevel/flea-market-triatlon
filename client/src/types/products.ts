export interface Review {
  id: number
  reviewer_username: string | null
  reviewer_tg_id: number
  rating: number
  comment: string | null
  created_at: string
}

export interface Seller {
  id: number
  username: string | null
  first_name: string | null
  last_name: string | null
  is_trusted_seller: boolean
  is_moderator: boolean
  rating: number
  review_count: number
  reviews: Review[]
}

export interface Product {
  id: number
  title: string
  price: number
  old_price?: number
  discount?: number
  cover_url: string | null
  image_urls: string[]
  category: string
  subcategory?: string
  country?: string
  city: string
  size?: string
  condition: string
  description?: string
  created_at: string
  seller?: Seller
}