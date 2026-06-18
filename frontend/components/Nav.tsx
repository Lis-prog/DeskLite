"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth, type UserRole } from "@/lib/auth-context";

type NavLink = { href: string; label: string };

function navLinksFor(role: UserRole): NavLink[] {
  switch (role) {
    case "customer":
      return [
        { href: "/tickets", label: "My Tickets" },
        { href: "/tickets/new", label: "New Ticket" },
      ];
    case "agent":
      return [{ href: "/tickets/queue", label: "My Queue" }];
    case "admin":
      return [
        { href: "/tickets", label: "All Tickets" },
        { href: "/tickets/new", label: "New Ticket" },
        { href: "/dashboard", label: "Dashboard" },
      ];
  }
}

function roleBadgeClass(role: UserRole) {
  const map: Record<UserRole, string> = {
    customer: "bg-brand-light text-brand",
    agent: "bg-amber-100 text-amber-700",
    admin: "bg-emerald-100 text-emerald-700",
  };
  return map[role];
}

export function Nav() {
  const { user, isLoading, logout } = useAuth();
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface shadow-sm">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-3">
        {/* Logo */}
        <Link href="/" className="text-lg font-bold text-brand">
          DeskLite
        </Link>

        {/* Nav links — only when authenticated */}
        {!isLoading && user && (
          <nav className="hidden gap-1 sm:flex" aria-label="Main navigation">
            {navLinksFor(user.role).map(({ href, label }) => {
              const active = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={href}
                  href={href}
                  className={[
                    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-brand text-white"
                      : "text-muted hover:bg-brand-light hover:text-brand",
                  ].join(" ")}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
        )}

        {/* Right side */}
        <div className="flex items-center gap-3">
          {isLoading && (
            <span className="h-4 w-24 animate-pulse rounded bg-border" />
          )}

          {!isLoading && user && (
            <>
              <span
                className={[
                  "hidden rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize sm:inline-block",
                  roleBadgeClass(user.role),
                ].join(" ")}
              >
                {user.role}
              </span>
              <span className="hidden max-w-[10rem] truncate text-sm text-muted sm:block">
                {user.full_name}
              </span>
              <button
                onClick={logout}
                className="rounded-md border border-border px-3 py-1.5 text-sm text-muted transition-colors hover:border-brand hover:text-brand"
              >
                Logout
              </button>
            </>
          )}

          {!isLoading && !user && (
            <Link
              href="/login"
              className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-dark"
            >
              Login
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
