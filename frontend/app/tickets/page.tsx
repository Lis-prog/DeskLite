"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PriorityBadge } from "@/components/PriorityBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/Spinner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type TicketStatus = "open" | "in_progress" | "resolved" | "closed";

type Ticket = {
  id: number;
  title: string;
  description: string;
  status: TicketStatus;
  priority: "low" | "medium" | "high" | "urgent";
  requester_id: number;
  assignee_id: number | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
};

type StatusFilter = TicketStatus | "all";

const STATUS_TABS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

const STORAGE_KEY_PREFIX = "desklite:filter:";

function defaultFilterFor(role: string | undefined): StatusFilter {
  if (role === "agent") return "in_progress";
  if (role === "customer") return "open";
  return "all";
}

function usePageMeta(role: string | undefined) {
  if (role === "customer") {
    return { title: "My Tickets", description: "Support requests you've submitted." };
  }
  if (role === "agent") {
    return { title: "My Queue", description: "Tickets currently assigned to you." };
  }
  return { title: "All Tickets", description: "Every support request across the system." };
}

export default function TicketsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { title, description } = usePageMeta(user?.role);

  useEffect(() => {
    if (user?.role === "agent") {
      router.replace("/tickets/queue");
    }
  }, [user?.role, router]);

  // ── mount guard ──────────────────────────────────────────────────────────
  // Render a consistent skeleton during SSR; switch to real UI only after
  // the component mounts on the client. This eliminates all hydration
  // mismatches caused by auth state, localStorage, or concurrent rendering.
  const [mounted, setMounted] = useState(false);

  // ── data ─────────────────────────────────────────────────────────────────
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  // ── filter ───────────────────────────────────────────────────────────────
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  useEffect(() => {
    // Client-only mount guard to avoid SSR hydration mismatches.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  // Apply role-aware default + saved preference after mount
  useEffect(() => {
    if (!mounted || !user) return;
    const key = `${STORAGE_KEY_PREFIX}${user.role}`;
    const saved = localStorage.getItem(key) as StatusFilter | null;
    const valid = saved && STATUS_TABS.some((t) => t.value === saved);
    // Syncs filter from localStorage (external system) after mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
    setStatusFilter(valid ? saved : defaultFilterFor(user.role));
  }, [mounted, user?.role]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleFilterChange(value: StatusFilter) {
    setStatusFilter(value);
    if (user) {
      localStorage.setItem(`${STORAGE_KEY_PREFIX}${user.role}`, value);
    }
  }

  // ── load tickets ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mounted) return;
    async function load() {
      try {
        const data = await api<Ticket[]>("/tickets");
        setTickets(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load tickets.");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [mounted]);

  const filtered =
    statusFilter === "all" ? tickets : tickets.filter((t) => t.status === statusFilter);

  // ── SSR skeleton (identical on server + client → no hydration mismatch) ──
  if (!mounted) {
    return (
      <div className="space-y-6">
        <div className="h-14 animate-pulse rounded-lg bg-border" />
        <div className="h-10 animate-pulse rounded-lg bg-border" />
        <div className="h-32 animate-pulse rounded-lg bg-border" />
      </div>
    );
  }

  // ── real UI (client-only) ─────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="mt-2 text-muted">{description}</p>
        </div>
        <Link
          href="/tickets/new"
          className="inline-flex items-center rounded-md bg-brand px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
        >
          New ticket
        </Link>
      </section>

      {/* Status filter tabs */}
      <div
        role="tablist"
        aria-label="Filter by status"
        className="flex flex-wrap gap-1 rounded-lg border border-border bg-surface p-1"
      >
        {STATUS_TABS.map((tab) => {
          const active = statusFilter === tab.value;
          return (
            <button
              key={tab.value}
              role="tab"
              aria-selected={active}
              onClick={() => handleFilterChange(tab.value)}
              className={[
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                active
                  ? "bg-brand text-white"
                  : "text-muted hover:bg-brand-light hover:text-brand",
              ].join(" ")}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface p-5">
          <Spinner size="h-4 w-4" />
          <p className="text-sm text-muted">Loading tickets...</p>
        </div>
      )}

      {/* Error */}
      {!isLoading && error && (
        <div className="rounded-lg border border-border bg-surface p-5">
          <p className="text-sm text-muted">{error}</p>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !error && filtered.length === 0 && (
        <div className="rounded-lg border border-border bg-surface p-5">
          <p className="text-sm text-muted">
            {statusFilter === "all"
              ? "No tickets found."
              : `No ${statusFilter.replace("_", " ")} tickets.`}
          </p>
        </div>
      )}

      {/* List */}
      {!isLoading && !error && filtered.length > 0 && (
        <div className="rounded-lg border border-border bg-surface">
          {filtered.map((ticket) => (
            <div
              key={ticket.id}
              className="flex flex-col gap-3 border-b border-border p-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="text-sm text-muted">Ticket #{ticket.id}</p>
                <Link
                  href={`/tickets/${ticket.id}`}
                  className="font-semibold text-brand underline"
                >
                  {ticket.title}
                </Link>
              </div>
              <div className="flex gap-2">
                <PriorityBadge priority={ticket.priority} />
                <StatusBadge status={ticket.status} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
