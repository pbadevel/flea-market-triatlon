// src/lib/session.ts
import { createServerFn } from "@tanstack/react-start";
import { redirect } from "@tanstack/react-router";
import { useAppSession } from "./session.server";


export const logoutFn = createServerFn().handler(async () => {
  const session = await useAppSession();
  await session.update({
    token: undefined,
    isAdmin: undefined,
    isModerator: undefined,
  });
  return {success: true}
});


export const getSession = createServerFn().handler(async () => {
  const session = await useAppSession();
  return {
    token: session.data?.token ?? null,
    isAdmin: session.data?.isAdmin ?? false,
    isModerator: session.data?.isModerator ?? false,
  };
});



export const verifySession = createServerFn()
.inputValidator((data?: { passLogin?: boolean }) => data ?? {passLogin: false})
.handler(async ({ data: { passLogin } = {} }) => {
  const session = await useAppSession();
  
  if (!session.data?.token && !passLogin) {
    throw redirect({ to: "/auth/login" });
  }
  
  return session.data
});

export const checkIsAdmin = createServerFn().handler(async () => {
  const session = await useAppSession();
  return session.data?.isAdmin === true;
});
