"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { LogoutButton } from "@/components/LogoutButton";
import { api } from "@/lib/api";

type User = {
  id: number;
  email: string;
  full_name: string;
  role: string;
};

export function AuthNav() {
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      try {
        const me = await api<User>("/auth/me");
        if (!cancelled) {
          setUser(me);
        }
      } catch {
        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setChecked(true);
        }
      }
    }

    setChecked(false);
    void loadUser();

    return () => {
      cancelled = true;
    };
  }, [pathname]);

  if (!checked) {
    return null;
  }

  if (user) {
    return (
      <>
        <span className="hidden text-sm text-muted sm:inline">{user.email}</span>
        <LogoutButton onLoggedOut={() => setUser(null)} />
      </>
    );
  }

  return (
    <>
      <Link href="/login" className="text-sm text-brand underline">
        Log in
      </Link>
      <Link href="/register" className="text-sm text-brand underline">
        Register
      </Link>
    </>
  );
}
