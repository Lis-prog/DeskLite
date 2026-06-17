"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { PriorityBadge } from "@/components/PriorityBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

type Ticket = {
  id: number;
  title: string;
  description: string;
  status: "open" | "in_progress" | "resolved" | "closed";
  priority: "low" | "medium" | "high" | "urgent";
  requester_id: number;
  assignee_id: number | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
};

type TicketDetailPageProps = {
  params: {
    ticketId: string;
  };
};

function formatDate(value: string | null) {
  if (!value) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function TicketDetailPage({ params }: TicketDetailPageProps) {
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadTicket() {
      try {
        const data = await api<Ticket>(`/tickets/${params.ticketId}`);
        setTicket(data);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Could not load ticket.");
        }
      } finally {
        setIsLoading(false);
      }
    }

    loadTicket();
  }, [params.ticketId]);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-surface p-5">
        <p className="text-sm text-muted">Loading ticket details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4 rounded-lg border border-border bg-surface p-5">
        <p className="text-sm text-muted">{error}</p>
        <Link className="text-sm font-medium text-brand underline" href="/tickets">
          Back to tickets
        </Link>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="space-y-4 rounded-lg border border-border bg-surface p-5">
        <p className="text-sm text-muted">Ticket not found.</p>
        <Link className="text-sm font-medium text-brand underline" href="/tickets">
          Back to tickets
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm text-muted">Ticket #{ticket.id}</p>
          <h1 className="mt-1 text-2xl font-bold">{ticket.title}</h1>
          <p className="mt-2 text-muted">
            Full ticket details for authorized users.
          </p>
        </div>

        <Link className="text-sm font-medium text-brand underline" href="/tickets">
          Back to tickets
        </Link>
      </section>

      <section className="rounded-lg border border-border bg-surface p-5">
        <div className="flex flex-wrap gap-2">
          <StatusBadge status={ticket.status} />
          <PriorityBadge priority={ticket.priority} />
        </div>

        <div className="mt-6 space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
            Description
          </h2>
          <p className="whitespace-pre-wrap text-sm">
            {ticket.description || "No description provided."}
          </p>
        </div>
      </section>

      <section className="grid gap-4 rounded-lg border border-border bg-surface p-5 sm:grid-cols-2">
        <div>
          <p className="text-sm text-muted">Requester ID</p>
          <p className="font-medium">{ticket.requester_id}</p>
        </div>

        <div>
          <p className="text-sm text-muted">Assignee ID</p>
          <p className="font-medium">{ticket.assignee_id ?? "Unassigned"}</p>
        </div>

        <div>
          <p className="text-sm text-muted">Created</p>
          <p className="font-medium">{formatDate(ticket.created_at)}</p>
        </div>

        <div>
          <p className="text-sm text-muted">Updated</p>
          <p className="font-medium">{formatDate(ticket.updated_at)}</p>
        </div>

        <div>
          <p className="text-sm text-muted">Resolved</p>
          <p className="font-medium">{formatDate(ticket.resolved_at)}</p>
        </div>
      </section>
    </div>
  );
}