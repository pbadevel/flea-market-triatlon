import { queryOptions } from '@tanstack/react-query';
import { fetchAds, fetchFilters, fetchProduct } from '@/lib/api/client/ads';
import { AdFilters } from '@/types/ad';

export const adsQueryOptions = (filters: AdFilters = {}) =>
  queryOptions({
    queryKey: ['ads', filters],
    queryFn: () => fetchAds(filters),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

export const filtersQueryOptions = () =>
  queryOptions({
    queryKey: ['filters'],
    queryFn: fetchFilters,
    staleTime: 60 * 60 * 1000,
    gcTime: 2 * 60 * 60 * 1000,
  });

export const productQueryOptions = (productId: string | number) =>
  queryOptions({
    queryKey: ['product', productId],
    queryFn: () => fetchProduct(productId),
    staleTime: 5 * 60 * 1000, // 5 минут
    gcTime: 10 * 60 * 1000, // 10 минут
  });