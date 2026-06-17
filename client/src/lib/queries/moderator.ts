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

export const pendingAdsQueryOptions = (token: string, page: number = 1) =>
  queryOptions({
    queryKey: ['admin', 'pending-ads', page],
    queryFn: () => fetchPendingAds(token, page),
    staleTime: 0, // Всегда свежие данные для модерации
    gcTime: 5 * 60 * 1000,
    enabled: !!token,
  });

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