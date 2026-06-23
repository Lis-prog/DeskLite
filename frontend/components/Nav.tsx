"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useState } from "react";
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

function NavLinkItem({
  href,
  label,
  active,
  onNavigate,
}: {
  href: string;
  label: string;
  active: boolean;
  onNavigate?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={[
        "block rounded-md px-3 py-2 text-sm font-medium transition-colors sm:py-1.5",
        active
          ? "bg-brand text-white"
          : "text-muted hover:bg-brand-light hover:text-brand",
      ].join(" ")}
    >
      {label}
    </Link>
  );
}

export function Nav() {
  const { user, isLoading, logout } = useAuth();
  const pathname = usePathname();
  const menuId = useId();
  const [mobileOpen, setMobileOpen] = useState(false);

  const links = user ? navLinksFor(user.role) : [];

  useEffect(() => {
    if (!mobileOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mobileOpen]);

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface shadow-sm">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        {/* Logo */}
        <Link href="/" className="text-lg font-bold text-brand">
          DeskLite
        </Link>

        {/* Desktop nav links */}
        {!isLoading && user && (
          <nav
            className="hidden gap-1 sm:flex"
            aria-label="Main navigation"
          >
            {links.map(({ href, label }) => {
              const active =
                pathname === href || pathname.startsWith(`${href}/`);
              return (
                <NavLinkItem
                  key={href}
                  href={href}
                  label={label}
                  active={active}
                />
              );
            })}
          </nav>
        )}

        {/* Right side */}
        <div className="flex items-center gap-2 sm:gap-3">
          {!isLoading && user && (
            <button
              type="button"
              className="rounded-md border border-border p-2 text-muted transition-colors hover:border-brand hover:text-brand focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 sm:hidden"
              aria-expanded={mobileOpen}
              aria-controls={menuId}
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
              onClick={() => setMobileOpen((open) => !open)}
            >
              <svg
                className="h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                aria-hidden="true"
              >
                {mobileOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18 18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
                  />
                )}
              </svg>
            </button>
          )}

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
                className="rounded-md border border-border px-3 py-1.5 text-sm text-muted transition-colors hover:border-brand hover:text-brand focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
              >
                Logout
              </button>
            </>
          )}

          {!isLoading && !user && (
            <Link
              href="/login"
              className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
            >
              Login
            </Link>
          )}
        </div>
      </div>

      {/* Mobile nav panel */}
      {!isLoading && user && mobileOpen && (
        <nav
          id={menuId}
          className="border-t border-border px-4 py-3 sm:hidden"
          aria-label="Mobile navigation"
        >
          <div className="mb-3 flex items-center gap-2">
            <span
              className={[
                "rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize",
                roleBadgeClass(user.role),
              ].join(" ")}
            >
              {user.role}
            </span>
            <span className="truncate text-sm text-muted">{user.full_name}</span>
          </div>
          <div className="space-y-1">
            {links.map(({ href, label }) => {
              const active =
                pathname === href || pathname.startsWith(`${href}/`);
              return (
                <NavLinkItem
                  key={href}
                  href={href}
                  label={label}
                  active={active}
                  onNavigate={() => setMobileOpen(false)}
                />
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}
