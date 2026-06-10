// src/lib/api/auth.ts
import { createServerFn } from '@tanstack/react-start';
import { apiRequest } from './api-request';
import {
  AUTH_TELEGRAM_INIT_ENDPOINT,
  AUTH_TELEGRAM_STATUS_ENDPOINT,
  AUTH_REGISTER_EMAIL_ENDPOINT,
  AUTH_LOGIN_EMAIL_ENDPOINT,
} from './endpoints';
import type {
  AuthResponse,
  TelegramAuthInitResponse,
  TelegramAuthStatusResponse,
  EmailRegisterData,
  EmailLoginData,
} from '@/types/auth';
import { useAppSession } from '../session';

// Telegram Auth
export const initTelegramAuthFn = createServerFn().handler(async () => {
  return await apiRequest<{ deeplink: string; session_token: string }>(
    AUTH_TELEGRAM_INIT_ENDPOINT,
    { method: "POST" }
  );
});

export const checkTelegramAuthStatusFn = createServerFn()
  .inputValidator((data: { session_token: string }) => data)
  .handler(async ({ data }) => {
    return await apiRequest<{
      status: "pending" | "completed" | "expired";
      token?: string;
      userId?: string;
      role?: string;
    }>(AUTH_TELEGRAM_STATUS_ENDPOINT, {
      method: "POST",
      body: data,
    });
  });

// Email Auth
export const registerEmailFn = createServerFn()
  .inputValidator((data: {
    email: string;
    password: string;
    firstName?: string;
    lastName?: string;
  }) => data)
  .handler(async ({ data }) => {
    const response = await apiRequest<{
      token: string;
      success: boolean;
      userId: string;
      role: string;
    }>(AUTH_REGISTER_EMAIL_ENDPOINT, {
      method: "POST",
      body: data,
    });

    if (response.token && response.success) {
      const session = await useAppSession();
      await session.update({
        token: response.token,
        isAdmin: response.role === "ADMIN",
        isModerator: response.role === "MODERATOR",
      });
    }

    return response;
  });

export const loginEmailFn = createServerFn()
  .inputValidator((data: { email: string; password: string }) => data)
  .handler(async ({ data }) => {
    const response = await apiRequest<{
      token: string;
      success: boolean;
      userId: string;
      role: string;
    }>(AUTH_LOGIN_EMAIL_ENDPOINT, {
      method: "POST",
      body: data,
    });

    if (response.token && response.success) {
      const session = await useAppSession();
      await session.update({
        token: response.token,
        isAdmin: response.role === "ADMIN",
        isModerator: response.role === "MODERATOR",
      });
    }

    return response;
  });