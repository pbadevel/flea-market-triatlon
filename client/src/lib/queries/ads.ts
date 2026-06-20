import { queryOptions } from '@tanstack/react-query';
import { fetchAds, fetchFilters, fetchProduct } from '@/lib/api/client/ads';
import type { AdFilters } from '@/types/ad';

export const adsQueryOptions = (filters: AdFilters = {}) =>
  queryOptions({
    queryKey: ['ads', filters],
    queryFn: () => fetchAds(filters) as Promise<any>,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

export const filtersQueryOptions = () =>
  queryOptions({
    queryKey: ['filters'],
    queryFn: () => fetchFilters() as Promise<any>,
    staleTime: 60 * 60 * 1000,
    gcTime: 2 * 60 * 60 * 1000,
  });

export const productQueryOptions = (productId: string | number) =>
  queryOptions({
    queryKey: ['product', productId],
    queryFn: () => fetchProduct(productId) as Promise<any>,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
