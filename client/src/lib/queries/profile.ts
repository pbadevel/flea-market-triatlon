import { queryOptions } from '@tanstack/react-query';
import { fetchMyProfile, fetchMyStats } from '@/lib/api/client/profile';

export const myProfileQueryOptions = (token: string) =>
  queryOptions({
    queryKey: ['profile', 'me'],
    queryFn: () => fetchMyProfile(token),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    enabled: !!token,
  });

export const myStatsQueryOptions = (token: string) =>
  queryOptions({
    queryKey: ['profile', 'stats'],
    queryFn: () => fetchMyStats(token),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    enabled: !!token,
  });