// src/lib/api/profile.ts
import { apiRequest } from '../api-request';
import { PROFILE_ME_ENDPOINT, PROFILE_STATS_ENDPOINT } from '../endpoints';
import type { UserProfile, UserProfileUpdate, UserStats } from '@/types/profile';

export const fetchMyProfile = async (token: string): Promise<UserProfile> => {
  return apiRequest<UserProfile>(PROFILE_ME_ENDPOINT, {
    method: 'GET',
    token,
  });
};

export const updateMyProfile = async (
  token: string,
  data: UserProfileUpdate,
): Promise<UserProfile> => {
  return apiRequest<UserProfile>(PROFILE_ME_ENDPOINT, {
    method: 'PATCH',
    token,
    body: data,
  });
};

export const fetchMyStats = async (token: string): Promise<UserStats> => {
  return apiRequest<UserStats>(PROFILE_STATS_ENDPOINT, {
    method: 'GET',
    token,
  });
};