"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PriorityBadge } from "@/components/PriorityBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { OverdueBadge } from "@/components/OverdueBadge";
import { Spinner } from "@/components/Spinner";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
type TicketPriority = "low" | "medium" | "high" | "urgent";

type Ticket = {
  id: number;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  requester_id: number;
  assignee_id: number | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  is_overdue: boolean;
};

type StatusFilter = TicketStatus | "all";
type PriorityFilter = TicketPriority | "all";

const STATUS_TABS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

const PRIORITY_OPTIONS: { value: PriorityFilter; label: string }[] = [
  { value: "all", label: "All priorities" },
  { value: "urgent", label: "Urgent" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

// Matches the backend `q` query param limit (see GET /tickets).
const SEARCH_MAX_LENGTH = 100;
const SEARCH_DEBOUNCE_MS = 300;

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

  // ── filters ──────────────────────────────────────────────────────────────
  // All filtering is delegated to the backend so role scope is always enforced
  // server-side; the list can never leak tickets the caller cannot see.
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStatusFilter(valid ? saved : defaultFilterFor(user.role));
  }, [mounted, user?.role]);

  // Debounce the search box so we query the API only when typing pauses.
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search.trim());
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [search]);

  function handleFilterChange(value: StatusFilter) {
    setStatusFilter(value);
    if (user) {
      localStorage.setItem(`${STORAGE_KEY_PREFIX}${user.role}`, value);
    }
  }

  function handleClearFilters() {
    setStatusFilter("all");
    setPriorityFilter("all");
    setSearch("");
    if (user) {
      localStorage.setItem(`${STORAGE_KEY_PREFIX}${user.role}`, "all");
    }
  }

  // ── load tickets (server-side filtering) ───────────────────────────────────
  useEffect(() => {
    if (!mounted) return;
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError("");
      try {
        const params = new URLSearchParams();
        if (statusFilter !== "all") params.set("status", statusFilter);
        if (priorityFilter !== "all") params.set("priority", priorityFilter);
        if (debouncedSearch) params.set("q", debouncedSearch);
        const query = params.toString();
        const data = await api<Ticket[]>(`/tickets${query ? `?${query}` : ""}`);
        if (!cancelled) setTickets(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load tickets.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [mounted, statusFilter, priorityFilter, debouncedSearch]);

  const hasActiveFilters =
    statusFilter !== "all" || priorityFilter !== "all" || debouncedSearch !== "";

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
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2",
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

      {/* Search box + priority filter bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <Input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            maxLength={SEARCH_MAX_LENGTH}
            placeholder="Search by title or description"
            aria-label="Search tickets"
          />
        </div>
        <div className="sm:w-52">
          <label htmlFor="priority-filter" className="sr-only">
            Filter by priority
          </label>
          <select
            id="priority-filter"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as PriorityFilter)}
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand focus:ring-offset-2"
          >
            {PRIORITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        {hasActiveFilters && (
          <button
            type="button"
            onClick={handleClearFilters}
            className="rounded-md px-3 py-2 text-sm font-medium text-muted transition-colors hover:text-brand focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          >
            Clear filters
          </button>
        )}
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
        <ErrorState title="Could not load tickets" description={error} />
      )}

      {/* Empty */}
      {!isLoading && !error && tickets.length === 0 && (
        <EmptyState
          title={
            hasActiveFilters ? "No tickets match your filters" : "No tickets yet"
          }
          description={
            hasActiveFilters
              ? "Try clearing filters or adjusting your search."
              : user?.role === "customer"
                ? "Create a new ticket to get help from the support team."
                : "Tickets will appear here as they are created."
          }
          action={
            !hasActiveFilters && user?.role !== "agent" ? (
              <Link
                href="/tickets/new"
                className="inline-flex items-center rounded-md bg-brand px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
              >
                New ticket
              </Link>
            ) : hasActiveFilters ? (
              <button
                type="button"
                onClick={handleClearFilters}
                className="rounded-md border border-border px-4 py-2 text-sm font-medium text-muted transition-colors hover:border-brand hover:text-brand focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
              >
                Clear filters
              </button>
            ) : undefined
          }
        />
      )}

      {/* List */}
      {!isLoading && !error && tickets.length > 0 && (
        <div className="rounded-lg border border-border bg-surface">
          {tickets.map((ticket) => (
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
              <div className="flex flex-wrap gap-2">
                {ticket.is_overdue && <OverdueBadge />}
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
