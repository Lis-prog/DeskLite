"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export type UserRole = "customer" | "agent" | "admin";

export type AuthUser = {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  created_at: string;
};

type AuthState =
  | { status: "loading" }
  | { status: "authenticated"; user: AuthUser }
  | { status: "unauthenticated" };

type AuthContextValue = {
  state: AuthState;
  user: AuthUser | null;
  isLoading: boolean;
  logout: () => Promise<void>;
  /** Call after a successful login to refresh the current-user snapshot. */
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({ status: "loading" });

  const fetchMe = useCallback(async () => {
    try {
      const user = await api<AuthUser>("/auth/me");
      setState({ status: "authenticated", user });
    } catch {
      setState({ status: "unauthenticated" });
    }
  }, []);

  useEffect(() => {
    // Initial auth check: fetchMe sets state only after the async request resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchMe();
  }, [fetchMe]);

  const logout = useCallback(async () => {
    try {
      await api<void>("/auth/logout", { method: "POST" });
    } catch {
      // best-effort — clear state regardless
    }
    setState({ status: "unauthenticated" });
    router.push("/login");
  }, [router]);

  const value: AuthContextValue = {
    state,
    user: state.status === "authenticated" ? state.user : null,
    isLoading: state.status === "loading",
    logout,
    refreshUser: fetchMe,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
