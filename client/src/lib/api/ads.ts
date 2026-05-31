import { AdFilters, AdsResponse, FilterConfig } from '@/types/ad';
import { apiRequest } from './api-request';
import { ADS_LIST_ENDPOINT, FILTER_ENDPOINT, PRODUCT_ENDPOINT } from './endpoints';
import { Product } from '@/types/products';


export const fetchAds = async (filters: AdFilters = {}): Promise<AdsResponse> => {
  const params = new URLSearchParams();
  
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.limit) params.append('limit', filters.limit.toString());
  if (filters.category) params.append('category', filters.category);
  if (filters.subcategory) params.append('subcategory', filters.subcategory);
  if (filters.country) params.append('country', filters.country);
  if (filters.city) params.append('city', filters.city);
  if (filters.condition) params.append('condition', filters.condition);
  if (filters.ad_type) params.append('ad_type', filters.ad_type);
  if (filters.minPrice) params.append('min_price', filters.minPrice.toString());
  if (filters.maxPrice) params.append('max_price', filters.maxPrice.toString());
  if (filters.search) params.append('search', filters.search);
  if (filters.sort) params.append('sort', filters.sort);


  const url = params.toString() ? `${ADS_LIST_ENDPOINT}?${params.toString()}` : ADS_LIST_ENDPOINT;
  
  return apiRequest<AdsResponse>(url, { method: 'GET' });
};



export const fetchProduct = async (productId: string | number): Promise<Product> => {
  return apiRequest<Product>(`${PRODUCT_ENDPOINT}/${productId}`, { method: 'GET' });
};

export const fetchFilters = async (): Promise<FilterConfig> => {
  return apiRequest<FilterConfig>(FILTER_ENDPOINT, { method: 'GET' });
};