// src/lib/api/admin/moderator.ts

import { apiRequest } from '../api-request';
import {   
    ADMIN_PENDING_ADS_ENDPOINT,
    ADMIN_ALL_ADS_ENDPOINT,
    ADMIN_MODERATE_ENDPOINT,
    ADMIN_STATS_ENDPOINT,
    ADMIN_AD_DETAIL_ENDPOINT,
 } from '../endpoints';

import type {
  AdminStats,
  AdminAdsResponse,
  AdminAd,
  ModerateAdPayload,
  AdminAdDetail,
} from '@/types/admin';

/** Получить статистику админки */
export const fetchAdminStats = async (token: string): Promise<AdminStats> => {
  return apiRequest<AdminStats>(ADMIN_STATS_ENDPOINT, {
    method: 'GET',
    token,
  });
};

/** Получить объявления на модерации */
export const fetchPendingAds = async (
  token: string,
  page: number = 1,
  limit: number = 20,
): Promise<AdminAdsResponse> => {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  });

  return apiRequest<AdminAdsResponse>(
    `${ADMIN_PENDING_ADS_ENDPOINT}?${params.toString()}`,
    {
      method: 'GET',
      token,
    },
  );
};

/** Получить все объявления с фильтрами */
export const fetchAllAds = async (
  token: string,
  filters: { status?: string; page?: number; limit?: number } = {},
): Promise<AdminAdsResponse> => {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.limit) params.append('limit', filters.limit.toString());

  const url = params.toString()
    ? `${ADMIN_ALL_ADS_ENDPOINT}?${params.toString()}`
    : ADMIN_ALL_ADS_ENDPOINT;

  return apiRequest<AdminAdsResponse>(url, {
    method: 'GET',
    token,
  });
};

/** Модерировать объявление (одобрить/отклонить) */
export const moderateAd = async (
  token: string,
  adId: number,
  payload: ModerateAdPayload,
): Promise<AdminAd> => {
  return apiRequest<AdminAd>(ADMIN_MODERATE_ENDPOINT(adId), {
    method: 'POST',
    token,
    body: payload,
  });
};

export const fetchAdminAdDetail = async (
  token: string,
  adId: number,
): Promise<AdminAdDetail> => {
  return apiRequest<AdminAdDetail>(ADMIN_AD_DETAIL_ENDPOINT(adId), {
    method: 'GET',
    token,
  });
};