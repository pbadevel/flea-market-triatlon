// src/lib/queries/phoneVerification.ts
import { queryOptions } from '@tanstack/react-query'
import { fetchPhoneStatus } from '@/lib/api/client/phoneVerification'

export const phoneStatusQueryOptions = (token: string) =>
  queryOptions({
    queryKey: ['phone-verification', 'status'],
    queryFn: () => fetchPhoneStatus(token),
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    enabled: !!token,
  })