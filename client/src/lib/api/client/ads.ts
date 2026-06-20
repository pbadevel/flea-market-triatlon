import { AdFilters, AdsResponse, FilterConfig, MyAd } from '@/types/ad';
import { apiRequest } from '../api-request';
import { ADS_LIST_ENDPOINT, CREATE_AD_ENDPOINT, FILTER_ENDPOINT, MY_ADS_ENDPOINT, PRODUCT_ENDPOINT } from '../endpoints';
import { Product } from '@/types/products';


export const fetchAds = async (filters: AdFilters = {}): Promise<AdsResponse> => {
  const params = new URLSearchParams();
  
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.limit) params.append('limit', filters.limit.toString());
  filters.categories?.forEach((value) => params.append('category', value));
  filters.subcategories?.forEach((value) => params.append('subcategory', value));
  filters.countries?.forEach((value) => params.append('country', value));
  filters.cities?.forEach((value) => params.append('city', value));
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


export const createAd = async (data: FormData, token: string): Promise<MyAd> => {
  return apiRequest<MyAd>(CREATE_AD_ENDPOINT, {
    method: 'POST',
    token,
    body: data,
  });
};

export const fetchMyAds = async (
  token: string,
  filters: { status?: string; page?: number; limit?: number } = {}
): Promise<{ data: MyAd[]; total: number; page: number; limit: number }> => {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.limit) params.append('limit', filters.limit.toString());

  const url = params.toString() ? `${MY_ADS_ENDPOINT}?${params.toString()}` : MY_ADS_ENDPOINT;
  
  return apiRequest(url, {
    method: 'GET',
    token,
  });
};



export const fetchAdForEdit = async (
  token: string,
  adId: number,
): Promise<MyAd> => {
  return apiRequest<MyAd>(`${PRODUCT_ENDPOINT}/${adId}`, {
    method: 'GET',
    token,
  });
};

export const updateAd = async (
  token: string,
  adId: number,
  data: FormData,
): Promise<MyAd> => {
  return apiRequest<MyAd>(`${ADS_LIST_ENDPOINT}/${adId}`, {
    method: 'PUT',
    token,
    body: data,
  });
};

export const resendAd = async (
  token: string,
  adId: number,
): Promise<MyAd> => {
  return apiRequest<MyAd>(`${ADS_LIST_ENDPOINT}/${adId}/resend`, {
    method: 'POST',
    token,
  });
};

export const deleteAd = async (
  token: string,
  adId: number,
): Promise<{ status: string; message: string }> => {
  return apiRequest(`${ADS_LIST_ENDPOINT}/${adId}`, {
    method: 'DELETE',
    token,
  });
};