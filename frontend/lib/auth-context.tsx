"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { api, refreshSession, setAccessToken } from "@/lib/api";
import type { LoginResponse, User } from "@/lib/types";

type Status = "loading" | "authenticated" | "anonymous";

type LoginResult = { requires2fa: false } | { requires2fa: true; challengeToken: string };

type AuthContextValue = {
  user: User | null;
  status: Status;
  signup: (email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<LoginResult>;
  verify2fa: (challengeToken: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

/** Keeps track of who is logged in, for every page of the website. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  const loadUser = useCallback(async () => {
    const me = await api<User>("/auth/me", { auth: true });
    setUserState(me);
    setStatus("authenticated");
  }, []);

  // On page load the access token is gone (it only lived in memory),
  // so try the refresh cookie to see if the user is still logged in.
  useEffect(() => {
    refreshSession().then(async (ok) => {
      if (ok) {
        try {
          await loadUser();
          return;
        } catch {
          // fall through to "anonymous"
        }
      }
      setStatus("anonymous");
    });
  }, [loadUser]);

  const finishLogin = useCallback(
    async (data: LoginResponse) => {
      setAccessToken(data.access_token);
      await loadUser();
    },
    [loadUser],
  );

  async function signup(email: string, password: string) {
    await api<User>("/auth/signup", { method: "POST", body: { email, password } });
  }

  async function login(email: string, password: string): Promise<LoginResult> {
    const data = await api<LoginResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    if (data.requires_2fa && data.challenge_token) {
      return { requires2fa: true, challengeToken: data.challenge_token };
    }
    await finishLogin(data);
    return { requires2fa: false };
  }

  async function verify2fa(challengeToken: string, code: string) {
    const data = await api<LoginResponse>("/auth/2fa/verify", {
      method: "POST",
      body: { challenge_token: challengeToken, code },
    });
    await finishLogin(data);
  }

  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      // Forget the user here even if the server couldn't be reached
      setAccessToken(null);
      setUserState(null);
      setStatus("anonymous");
    }
  }

  return (
    <AuthContext
      value={{ user, status, signup, login, verify2fa, logout, setUser: setUserState }}
    >
      {children}
    </AuthContext>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return value;
}
