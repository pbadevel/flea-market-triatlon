// src/types/ad.ts

export interface Ad {
  id: number;
  title: string;
  price: number;
  old_price?: number;
  discount?: number;
  cover_url: string | null;
  description?: string;
  category: string;
  subcategory?: string;
  country?: string;
  city?: string;
  condition: 'new' | 'used' | 'unknown';
  ad_type: 'sale' | 'rent';
  contact_method: string;
  size?: string;
  seller_id?: number;
  seller_name?: string;
  seller_rating?: number;
  created_at: string;
  updated_at?: string;
  photos?: string[];
  specifications?: Record<string, string>;
}

export interface AdsResponse {
  data: Ad[];
  total: number;
  page: number;
  limit: number;
}

export type SortOption = 'created_at_desc' | 'created_at_asc' | 'price_asc' | 'price_desc';

export interface AdFilters {
  page?: number;
  limit?: number;
  /** Whole categories (all items in category) */
  categories?: string[];
  /** Specific subcategory keys from filter config */
  subcategories?: string[];
  countries?: string[];
  cities?: string[];
  condition?: 'new' | 'used' | 'unknown';
  ad_type?: 'sale' | 'rent';
  minPrice?: number;
  maxPrice?: number;
  search?: string;
  sort?: SortOption;
}

export interface FilterOption {
  key: string;
  label: string;
  count?: number;
}

export interface FilterGroup {
  name: string;
  items: FilterOption[];
}


export interface GeoItem {
  key: string;
  name: string;
  flag?: string;
  cities?: string[];
}

export interface SubcategoryItem {
  key: string;
  label: string;
  requires_size?: boolean;
}






export interface MyAd extends Ad {
  id: number;
  title: string;
  price: number;
  city: string;
  country?: string;
  category: string;
  contact_method: string;
  subcategory?: string;
  status: 'pending' | 'approved' | 'rejected' | 'sold' | 'removed';
  rejection_reason?: string;
  created_at: string;
  channel_message_id?: number;
  photo_ids?: number[];
}

export interface AdCreateData {
  title: string;
  price: number;
  city: string;
  country?: string;
  category: string;
  subcategory?: string;
  size?: string;
  condition: string;
  description?: string;
  ad_type?: string;
  delivery_method?: string;
  contact_method?: string;
  photos: File[];
}





export interface CategoryItem {
  key: string;
  label: string;
  requires_size?: boolean;
}

export interface CategoryGroup {
  name: string;
  items: CategoryItem[];
}

export interface CategoryFilter {
  key: string;
  label: string;
  groups?: CategoryGroup[];
  items?: CategoryItem[];
}

export interface GeoCountry {
  key: string;
  name: string;
  flag: string;
  cities: string[];
}

export interface FilterConfig {
  categories: CategoryFilter[];
  countries: GeoCountry[];
  default_cities: string[];
  conditions: { key: string; label: string }[];
  sizes: string[];
  ad_types: { key: string; label: string }[];
}