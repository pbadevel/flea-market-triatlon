// src/types/auth.ts
export interface AuthResponse {
  token: string;
  success: boolean;
  userId: string;
  role: string;
}

export interface TelegramAuthInitResponse {
  deeplink: string;
  session_token: string;
}

export interface TelegramAuthStatusResponse {
  status: "pending" | "completed" | "expired";
  token?: string;
  userId?: string;
  role?: string;
}

export interface EmailRegisterData {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
}

export interface EmailLoginData {
  email: string;
  password: string;
}

export type AuthMethod = 'telegram' | 'email';