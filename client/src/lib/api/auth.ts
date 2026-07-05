// src/lib/api/auth.ts
import { createServerFn } from '@tanstack/react-start';
import { useAppSession } from '../session';

const API = 'http://127.0.0.1:8000/v1'

async function apiCall<T>(path: string, options?: { method?: string; body?: unknown; token?: string }): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (options?.token) headers['Authorization'] = `Bearer ${options.token}`
  const res = await fetch(`${API}${path}`, {
    method: options?.method || 'GET',
    headers,
    body: options?.body ? JSON.stringify(options.body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail))
  }
  return await res.json()
}

// Telegram Auth
export const initTelegramAuthFn = createServerFn().handler(async () => {
  return await apiCall<{ deeplink: string; session_token: string }>('/auth/telegram/init', { method: 'POST' })
})

export const initTelegramLinkFn = createServerFn()
  .inputValidator((data: { token: string }) => data)
  .handler(async ({ data }) => {
    return await apiCall<{ deeplink: string; session_token: string }>('/auth/telegram/init', { method: 'POST', token: data.token })
  })

export const checkTelegramAuthStatusFn = createServerFn()
  .inputValidator((data: { session_token: string }) => data)
  .handler(async ({ data }) => {
    const response = await apiCall<{ status: 'pending' | 'completed' | 'expired'; token?: string; userId?: string; role?: string }>(
      '/auth/telegram/status', { method: 'POST', body: data }
    )
    return response
  })

// Email Auth
export const registerEmailFn = createServerFn()
  .inputValidator((data: { email: string; password: string; firstName: string; lastName?: string; phone?: string; preferredContact: string; contactValue: string }) => data)
  .handler(async ({ data }) => {
    return await apiCall<{ success: boolean; message: string; email: string }>('/auth/register/email', { method: 'POST', body: data })
  })

export const loginEmailFn = createServerFn()
  .inputValidator((data: { email: string; password: string }) => data)
  .handler(async ({ data }) => {
    const response = await apiCall<{ token: string; success: boolean; userId: string; role: string }>(
      '/auth/login/email', { method: 'POST', body: data }
    )
    if (response.token && response.success) {
      const session = await useAppSession()
      await session.update({ token: response.token, isAdmin: response.role === 'ADMIN', isModerator: response.role === 'MODERATOR' })
    }
    return response
  })

export const resendConfirmationFn = createServerFn()
  .inputValidator((data: { email: string }) => data)
  .handler(async ({ data }) => {
    return await apiCall<{ success: boolean; message: string }>('/auth/resend-confirmation', { method: 'POST', body: data })
  })
