// src/lib/session.server.ts
import { useSession } from "@tanstack/react-start/server";

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
      secure: false,
      sameSite: "lax",
    },
  });
}
