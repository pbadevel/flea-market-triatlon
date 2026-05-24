export interface SubcategoryItem {
  key: string;
  label: string;
  requires_size: boolean;
}

export interface SubcategoryGroup {
  name: string;
  items: SubcategoryItem[];
}

export interface CategoryFilter {
  key: string;
  label: string;
  groups: SubcategoryGroup[] | null;
  items: SubcategoryItem[] | null;
  default_tags: string[];
}

export interface GeoItem {
  key: string;
  name: string;
  flag: string | null;
  cities: string[];
}

export interface FilterConfig {
  categories: CategoryFilter[];
  countries: GeoItem[];
  default_cities: string[];
  conditions: { key: string; label: string }[];
  sizes: string[];
  ad_types: { key: string; label: string }[];
}

export interface ProductFilters {
  category?: string;
  subcategory?: string;
  country?: string;
  city?: string;
  condition?: string;
  ad_type?: string;
  min_price?: number;
  max_price?: number;
  page?: number;
  limit?: number;
}