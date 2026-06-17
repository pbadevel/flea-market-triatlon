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
    cookie: {
      // Set to false for HTTP IP-address testing, true for HTTPS production
      secure: false, // CHANGE IT WHEN PRODUCION
      sameSite: "lax",
    },
  });
}


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



export const verifySession = createServerFn().handler(async () => {
  const session = await useAppSession();

  // console.log("verifying", session.data)
  
  if (!session.data?.token) {
    throw redirect({ to: "/auth/login" });
  }
  
  return session.data
});

export const checkIsAdmin = createServerFn().handler(async () => {
  const session = await useAppSession();
  return session.data?.isAdmin === true;
});