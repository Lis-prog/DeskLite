"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { PriorityBadge } from "@/components/PriorityBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/Button";
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

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadTickets() {
      try {
        const data = await api<Ticket[]>("/tickets");
        setTickets(data);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Could not load tickets.");
        }
      } finally {
        setIsLoading(false);
      }
    }

    loadTickets();
  }, []);

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tickets</h1>
          <p className="mt-2 text-muted">
            View and track support requests in one place.
          </p>
        </div>

        <Link href="/tickets/new">
          <Button type="button">New ticket</Button>
        </Link>
      </section>

      {isLoading && (
        <div className="rounded-lg border border-border bg-surface p-5">
          <p className="text-sm text-muted">Loading tickets...</p>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-border bg-surface p-5">
          <p className="text-sm text-muted">{error}</p>
        </div>
      )}

      {!isLoading && !error && tickets.length === 0 && (
        <div className="rounded-lg border border-border bg-surface p-5">
          <p className="text-sm text-muted">No tickets found.</p>
        </div>
      )}

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