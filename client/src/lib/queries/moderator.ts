// src/lib/queries/moderator.ts
import { queryOptions } from '@tanstack/react-query';
import { fetchAdminStats, fetchPendingAds, fetchAllAds, fetchAdminAdDetail } from '@/lib/api/admin/moderator';

export const adminStatsQueryOptions = (token: string) =>
  queryOptions({
    queryKey: ['admin', 'stats'],
    queryFn: () => fetchAdminStats(token),
    staleTime: 30 * 1000, // 30 секунд
    gcTime: 5 * 60 * 1000, // 5 минут
    enabled: !!token,
  });

export function pendingAdsQueryOptions(
  token: string,
  params: { page: number; limit: number } = { page: 1, limit: 10 },
) {
  return {
    queryKey: ['admin', 'pending-ads', params.page, params.limit],
    queryFn: () => fetchPendingAds(token, params),
    staleTime: 1000 * 60 * 5, // 5 минут
  }
}
export const allAdsQueryOptions = (
  token: string,
  filters: { status?: string; page?: number; limit?: number } = {},
) =>
  queryOptions({
    queryKey: ['admin', 'all-ads', filters],
    queryFn: () => fetchAllAds(token, filters),
    staleTime: 0,
    gcTime: 5 * 60 * 1000,
    enabled: !!token,
  });



export const adminAdDetailQueryOptions = (token: string, adId: number) =>
  queryOptions({
    queryKey: ['admin', 'ad-detail', adId],
    queryFn: () => fetchAdminAdDetail(token, adId),
    staleTime: 0, // Всегда свежие данные
    gcTime: 5 * 60 * 1000,
    enabled: !!token && adId > 0,
  });