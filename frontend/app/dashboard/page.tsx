"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { BarChart } from "@/components/ui/BarChart";
import { StatusBadge } from "@/components/StatusBadge";
import { PriorityBadge } from "@/components/PriorityBadge";
import { Spinner } from "@/components/Spinner";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { RequireAdmin } from "@/components/RequireAdmin";
import { Button } from "@/components/ui/Button";
import {
  api,
  getAgentWorkload,
  getResolutionTime,
  getTicketMetrics,
  type AgentWorkload,
  type ResolutionTime,
  type TicketMetrics,
  type TicketPriority,
  type TicketStatus,
} from "@/lib/api";

type Ticket = {
  id: number;
  title: string;
  status: TicketStatus;
  priority: TicketPriority;
  requester_id: number;
  assignee_id: number | null;
  created_at: string;
};

type User = {
  id: number;
  email: string;
  full_name: string;
  role: "customer" | "agent" | "admin";
};

const STATUS_ORDER: TicketStatus[] = ["open", "in_progress", "resolved", "closed"];
const PRIORITY_ORDER: TicketPriority[] = ["urgent", "high", "medium", "low"];

const STATUS_COLOR: Record<TicketStatus, string> = {
  open: "bg-status-open",
  in_progress: "bg-status-progress",
  resolved: "bg-status-resolved",
  closed: "bg-status-closed",
};

const PRIORITY_COLOR: Record<TicketPriority, string> = {
  urgent: "bg-priority-urgent",
  high: "bg-priority-high",
  medium: "bg-priority-medium",
  low: "bg-priority-low",
};

const STATUS_LABELS: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  resolved: "Resolved",
  closed: "Closed",
};

/** Last N days as "Mon Jun 16" labels. */
function lastNDays(n: number): string[] {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (n - 1 - i));
    return d.toLocaleDateString("en", { month: "short", day: "numeric" });
  });
}

function toDateLabel(iso: string) {
  return new Date(iso).toLocaleDateString("en", {
    month: "short",
    day: "numeric",
  });
}

/** Human-readable duration from seconds, e.g. 9000 → "2h 30m". */
function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const totalMinutes = Math.round(seconds / 60);
  if (totalMinutes < 60) return `${totalMinutes}m`;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours < 24) return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
  const days = Math.floor(hours / 24);
  const remHours = hours % 24;
  return remHours ? `${days}d ${remHours}h` : `${days}d`;
}

export default function DashboardPage() {
  return (
    <RequireAdmin>
      <DashboardContent />
    </RequireAdmin>
  );
}

function DashboardContent() {
  const [metrics, setMetrics] = useState<TicketMetrics | null>(null);
  const [workload, setWorkload] = useState<AgentWorkload[]>([]);
  const [resolution, setResolution] = useState<ResolutionTime | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        // Aggregates come from the metrics API (server-side, role-scoped);
        // the raw ticket list still feeds the trend + recent-tickets views,
        // and the user list feeds the team head-count cards.
        const [metricsData, workloadData, resolutionData, ticketData, userData] =
          await Promise.all([
            getTicketMetrics(),
            getAgentWorkload(),
            getResolutionTime(),
            api<Ticket[]>("/tickets"),
            api<User[]>("/admin/users"),
          ]);
        setMetrics(metricsData);
        setWorkload(workloadData);
        setResolution(resolutionData);
        setTickets(ticketData);
        setUsers(userData);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Could not load dashboard data."
        );
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, []);

  const agents = useMemo(() => users.filter((u) => u.role === "agent"), [users]);
  const customers = useMemo(
    () => users.filter((u) => u.role === "customer"),
    [users]
  );

  // Active tickets per agent, straight from /metrics/agents/workload.
  const agentLoad = useMemo(
    () =>
      [...workload]
        .sort((a, b) => b.active_ticket_count - a.active_ticket_count)
        .map((a) => ({ label: a.full_name, value: a.active_ticket_count })),
    [workload]
  );

  // 7-day trend
  const trendDays = 7;
  const trendData = useMemo(() => {
    const labels = lastNDays(trendDays);
    const counts: Record<string, number> = {};
    for (const t of tickets) {
      const label = toDateLabel(t.created_at);
      counts[label] = (counts[label] ?? 0) + 1;
    }
    return labels.map((label) => ({
      label,
      value: counts[label] ?? 0,
      colorClass: "bg-brand",
    }));
  }, [tickets]);

  const recentTickets = useMemo(
    () =>
      [...tickets]
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
        .slice(0, 8),
    [tickets]
  );

  // ── Render ───────────────────────────────────────────────────────────────
  if (isLoading && !error) {
    return (
      <div className="flex items-center justify-center py-32">
        <Spinner size="h-8 w-8" label="Loading dashboard…" />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load dashboard"
        description={error}
        action={
          <Button type="button" onClick={() => window.location.reload()}>
            Retry
          </Button>
        }
      />
    );
  }

  if (!metrics || !resolution) {
    return null;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="mt-1 text-sm text-muted">
          Live overview of all support activity.
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard label="Total tickets" value={metrics.total} />
        <StatCard
          label="Open"
          value={metrics.by_status.open}
          accent="text-status-open"
        />
        <StatCard
          label="In progress"
          value={metrics.by_status.in_progress}
          accent="text-status-progress"
        />
        <StatCard
          label="Unassigned"
          value={metrics.unassigned}
          accent={metrics.unassigned > 0 ? "text-priority-urgent" : undefined}
        />
        <StatCard
          label="Avg resolution"
          value={formatDuration(resolution.average_seconds)}
        />
      </div>

      {/* Charts row */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Status distribution */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Status distribution</h2>
          </CardHeader>
          <CardBody>
            <BarChart
              data={STATUS_ORDER.map((s) => ({
                label: STATUS_LABELS[s],
                value: metrics.by_status[s],
                colorClass: STATUS_COLOR[s],
              }))}
            />
          </CardBody>
        </Card>

        {/* Priority distribution */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Priority distribution</h2>
          </CardHeader>
          <CardBody>
            <BarChart
              data={PRIORITY_ORDER.map((p) => ({
                label: p.charAt(0).toUpperCase() + p.slice(1),
                value: metrics.by_priority[p],
                colorClass: PRIORITY_COLOR[p],
              }))}
            />
          </CardBody>
        </Card>

        {/* Agent load */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">
              Active tickets per agent
            </h2>
          </CardHeader>
          <CardBody>
            {agentLoad.length === 0 ? (
              <p className="text-sm text-muted">No agents yet.</p>
            ) : (
              <BarChart data={agentLoad} />
            )}
          </CardBody>
        </Card>
      </div>

      {/* 7-day trend */}
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Tickets created — last 7 days</h2>
        </CardHeader>
        <CardBody>
          <BarChart data={trendData} />
        </CardBody>
      </Card>

      {/* Resolution time */}
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Resolution time</h2>
        </CardHeader>
        <CardBody>
          {resolution.resolved_count === 0 ? (
            <p className="text-sm text-muted">
              No resolved tickets yet — stats appear once tickets are resolved.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-xs text-muted">Average</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">
                  {formatDuration(resolution.average_seconds)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted">Median</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">
                  {formatDuration(resolution.median_seconds)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted">Resolved tickets</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">
                  {resolution.resolved_count}
                </p>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Team counts */}
      <div className="grid gap-6 sm:grid-cols-3">
        <Card>
          <CardBody>
            <p className="text-xs text-muted">Agents</p>
            <p className="mt-1 text-3xl font-bold tabular-nums">
              {agents.length}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-xs text-muted">Customers</p>
            <p className="mt-1 text-3xl font-bold tabular-nums">
              {customers.length}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-xs text-muted">Total users</p>
            <p className="mt-1 text-3xl font-bold tabular-nums">
              {users.length}
            </p>
          </CardBody>
        </Card>
      </div>

      {/* Recent tickets */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent tickets</h2>
            <Link href="/tickets" className="text-sm text-brand underline">
              View all
            </Link>
          </div>
        </CardHeader>

        {recentTickets.length === 0 ? (
          <CardBody>
            <EmptyState
              title="No tickets yet"
              description="New tickets will appear here as they are created."
            />
          </CardBody>
        ) : (
          <div>
            {recentTickets.map((ticket) => (
              <div
                key={ticket.id}
                className="flex flex-col gap-2 border-b border-border p-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="text-xs text-muted">#{ticket.id}</p>
                  <Link
                    href={`/tickets/${ticket.id}`}
                    className="text-sm font-medium text-brand underline"
                  >
                    {ticket.title}
                  </Link>
                </div>
                <div className="flex shrink-0 gap-2">
                  <PriorityBadge priority={ticket.priority} />
                  <StatusBadge status={ticket.status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number | string;
  accent?: string;
}) {
  return (
    <Card>
      <CardBody>
        <p className="text-xs text-muted">{label}</p>
        <p
          className={`mt-1 text-3xl font-bold tabular-nums ${accent ?? "text-slate-900"}`}
        >
          {value}
        </p>
      </CardBody>
    </Card>
  );
}
