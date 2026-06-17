import { apiRequest } from '../api-request';
import { ADMIN_USERS_ENDPOINT } from '../endpoints';
import type { AdminUsersResponse } from '@/types/admin';

export const fetchUsers = async (token: string, search?: string, page = 1): Promise<AdminUsersResponse> => {
  const params = new URLSearchParams({ page: String(page), limit: '20' });
  if (search) params.set('search', search);
  return apiRequest<AdminUsersResponse>(`${ADMIN_USERS_ENDPOINT}?${params}`, { method: 'GET', token });
};

export const updateUser = async (token: string, userId: number, data: { role?: string; is_trusted_seller?: boolean }) =>
  apiRequest(`${ADMIN_USERS_ENDPOINT}/${userId}`, { method: 'PUT', token, body: data });

export const banUser = async (token: string, userId: number) =>
  apiRequest(`${ADMIN_USERS_ENDPOINT}/${userId}/ban`, { method: 'POST', token });

export const unbanUser = async (token: string, userId: number) =>
  apiRequest(`${ADMIN_USERS_ENDPOINT}/${userId}/unban`, { method: 'POST', token });

export const makeAdmin = async (token: string, userId: number) =>
  apiRequest(`${ADMIN_USERS_ENDPOINT}/${userId}/make-admin`, { method: 'POST', token });
