"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { Spinner } from "@/components/Spinner";
import { useAuth } from "@/lib/auth-context";

/**
 * Client-side access guard for admin-only pages.
 *
 * Renders `children` only once the session is resolved AND the user is an admin.
 * Unauthenticated visitors are sent to `/login`; signed-in non-admins are sent
 * to `/tickets`. While auth is loading (or a redirect is pending) a spinner is
 * shown and the protected content is never mounted.
 *
 * This is a UX-level gate: the authoritative check still lives in the backend,
 * which returns 403 for the dashboard's admin-only data sources.
 */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (user.role !== "admin") {
      router.replace("/tickets");
    }
  }, [user, isLoading, router]);

  if (isLoading || !user || user.role !== "admin") {
    return (
      <div className="flex items-center justify-center py-32">
        <Spinner size="h-8 w-8" label="Checking access…" />
      </div>
    );
  }

  return <>{children}</>;
}
