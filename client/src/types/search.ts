export interface SearchResult {
  id: number;
  title: string;
  price: number;
  old_price?: number;
  discount?: number;
  cover_url: string;
  category: string;
  subcategory?: string;
}

export interface SearchResponse {
  data: SearchResult[];
  total: number;
  query: string;
}

export interface SearchFilters {
  query: string;
  category?: string;
  limit?: number;
}