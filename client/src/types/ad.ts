// src/types/ad.ts

export interface Ad {
  id: number;
  title: string;
  price: number;
  old_price?: number;
  discount?: number;
  cover_url: string;
  description?: string;
  category?: string;
  subcategory?: string;
  country?: string;
  city?: string;
  condition?: string;
  ad_type?: string;
  seller_id?: number;
  seller_name?: string;
  seller_rating?: number;
  created_at: string;
  updated_at?: string;
  photos?: string[];
  specifications?: Record<string, string>;
}

export interface AdFilters {
  page?: number;
  limit?: number;
  category?: string;
  subcategory?: string;
  country?: string;
  city?: string;
  minPrice?: number;
  maxPrice?: number;
  search?: string;
}


export interface AdsResponse {
  data: Ad[];
  total: number;
  page: number;
  limit: number;
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

export interface CategoryFilter {
  key: string;
  label: string;
  groups?: SubcategoryGroup[] | null;
  items?: SubcategoryItem[] | null;
  default_tags?: string[];
}

export interface GeoItem {
  key: string;
  name: string;
  flag?: string | null;
  cities?: string[];
}

export interface FilterConfig {
  categories: CategoryFilter[];
  countries: GeoItem[];
  default_cities: string[];
  conditions: { key: string; label: string }[];
  sizes: string[];
  ad_types: { key: string; label: string }[];
}