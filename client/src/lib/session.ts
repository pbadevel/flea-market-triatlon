// src/lib/session.ts
import { createServerFn } from "@tanstack/react-start";
import { useSession } from "@tanstack/react-start/server";
import { redirect } from "@tanstack/react-router";

type SessionUser = {
  token?: string;
  isAdmin?: boolean;
  isModerator?: boolean;
};

export function useAppSession() {
  return useSession<SessionUser>({
    password: process.env.SESSION_PASSWORD!,
    maxAge: 60 * 60 * 24 * 7,
  });
}


export const getSession = createServerFn().handler(async () => {
  const session = await useAppSession();
  return {
    token: session.data?.token ?? null,
    isAdmin: session.data?.isAdmin ?? false,
    isModerator: session.data?.isModerator ?? false,
  };
});

// Тестовая авторизация
export const testLoginFn = createServerFn().handler(async () => {
  const response = await fetch(`${process.env.VITE_BACKEND_DOMAIN}/v1/auth-test/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tg_user_id: 123456789 }),
  });
  
  const data = await response.json();

  console.log(data)
  
  if (data.token && data.success) {
    const session = await useAppSession();
    await session.update({
      token: data.token,
      isAdmin: data.role === "ADMIN",
      isModerator: data.role === "MODERATOR"
    });
  }
  
  return data;
});

export const verifySession = createServerFn().handler(async () => {
  const session = await useAppSession();
  
  if (!session.data?.token) {
    throw redirect({ to: "/auth/login" });
  }
  
  return session.data
});

export const checkIsAdmin = createServerFn().handler(async () => {
  const session = await useAppSession();
  return session.data?.isAdmin === true;
});