// src/types/ad.ts

export interface Ad {
  id: number;
  title: string;
  price: number;
  old_price?: number;
  discount?: number;
  cover_url: string;
  description?: string;
  category: string;
  subcategory?: string;
  country?: string;
  city?: string;
  condition: 'new' | 'used' | 'unknown';
  ad_type: 'sale' | 'rent';
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

export interface CategoryFilter {
  key: string;
  label: string;
  groups?: FilterGroup[];
  items?: FilterOption[];
  default_tags?: string[];
}

export interface GeoItem {
  key: string;
  name: string;
  flag?: string;
  cities?: string[];
}

export interface FilterConfig {
  categories: CategoryFilter[];
  countries: GeoItem[];
  conditions: { key: string; label: string }[];
  ad_types: { key: string; label: string }[];
  sizes: string[];
  default_cities: string[];
}

export interface SubcategoryItem {
  key: string;
  label: string;
  requires_size?: boolean;
}

export interface SubcategoryGroup {
  name: string;
  items: SubcategoryItem[];
}

