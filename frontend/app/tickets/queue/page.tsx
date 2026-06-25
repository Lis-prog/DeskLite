"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PriorityBadge } from "@/components/PriorityBadge";
import { OverdueBadge } from "@/components/OverdueBadge";
import { Spinner } from "@/components/Spinner";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardBody } from "@/components/ui/Card";
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

type QueueFilter = "active" | TicketStatus | "all";

const QUEUE_TABS: { value: QueueFilter; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
  { value: "all", label: "All" },
];

const PRIORITY_RANK: Record<TicketPriority, number> = {
  urgent: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const FILTER_STORAGE_KEY = "desklite:agent-queue:filter";

function matchesFilter(ticket: Ticket, filter: QueueFilter): boolean {
  if (filter === "all") return true;
  if (filter === "active") {
    return ticket.status === "open" || ticket.status === "in_progress";
  }
  return ticket.status === filter;
}

function sortQueue(a: Ticket, b: Ticket): number {
  const byPriority = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
  if (byPriority !== 0) return byPriority;
  return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
}

function formatCreatedAt(iso: string) {
  return new Date(iso).toLocaleDateString("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AgentQueuePage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  const [mounted, setMounted] = useState(false);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<QueueFilter>("active");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || authLoading) return;
    if (!user) return;
    if (user.role !== "agent") {
      router.replace("/tickets");
    }
  }, [mounted, authLoading, user, router]);

  useEffect(() => {
    if (!mounted) return;
    const saved = localStorage.getItem(FILTER_STORAGE_KEY) as QueueFilter | null;
    const valid = saved && QUEUE_TABS.some((tab) => tab.value === saved);
    if (valid) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFilter(saved);
    }
  }, [mounted]);

  useEffect(() => {
    if (!mounted || authLoading || user?.role !== "agent") return;

    async function load() {
      setIsLoading(true);
      setError("");
      try {
        const data = await api<Ticket[]>("/tickets");
        setTickets(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load your queue.");
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [mounted, authLoading, user?.role]);

  function handleFilterChange(value: QueueFilter) {
    setFilter(value);
    localStorage.setItem(FILTER_STORAGE_KEY, value);
  }

  const stats = useMemo(() => {
    const open = tickets.filter((t) => t.status === "open").length;
    const inProgress = tickets.filter((t) => t.status === "in_progress").length;
    return {
      open,
      inProgress,
      active: open + inProgress,
      total: tickets.length,
    };
  }, [tickets]);

  const filtered = useMemo(
    () => tickets.filter((t) => matchesFilter(t, filter)).sort(sortQueue),
    [tickets, filter]
  );

  if (!mounted || authLoading || user?.role !== "agent") {
    return (
      <div className="space-y-6">
        <div className="h-14 animate-pulse rounded-lg bg-border" />
        <div className="h-24 animate-pulse rounded-lg bg-border" />
        <div className="h-32 animate-pulse rounded-lg bg-border" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold">My Queue</h1>
        <p className="mt-2 text-muted">
          Tickets assigned to you, sorted by priority and age.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardBody>
            <p className="text-sm text-muted">Active</p>
            <p className="mt-1 text-2xl font-bold text-brand">{stats.active}</p>
            <p className="mt-1 text-xs text-muted">Open or in progress</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-sm text-muted">Open</p>
            <p className="mt-1 text-2xl font-bold">{stats.open}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-sm text-muted">In progress</p>
            <p className="mt-1 text-2xl font-bold">{stats.inProgress}</p>
          </CardBody>
        </Card>
      </section>

      <div
        role="tablist"
        aria-label="Filter queue by status"
        className="flex flex-wrap gap-1 rounded-lg border border-border bg-surface p-1"
      >
        {QUEUE_TABS.map((tab) => {
          const active = filter === tab.value;
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

      {isLoading && (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface p-5">
          <Spinner size="h-4 w-4" />
          <p className="text-sm text-muted">Loading your queue...</p>
        </div>
      )}

      {!isLoading && error && (
        <ErrorState title="Could not load queue" description={error} />
      )}

      {!isLoading && !error && filtered.length === 0 && (
        <EmptyState
          title={
            filter === "active"
              ? "No active tickets in your queue"
              : "No tickets match this filter"
          }
          description={
            filter === "active"
              ? "When a manager assigns you a ticket, it will appear here."
              : "Try another status filter to see assigned tickets."
          }
        />
      )}

      {!isLoading && !error && filtered.length > 0 && (
        <div className="rounded-lg border border-border bg-surface">
          {filtered.map((ticket) => (
            <div
              key={ticket.id}
              className="flex flex-col gap-3 border-b border-border p-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="text-sm text-muted">
                  Ticket #{ticket.id} · Requester #{ticket.requester_id} ·{" "}
                  {formatCreatedAt(ticket.created_at)}
                </p>
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
