"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { PriorityBadge } from "@/components/PriorityBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { CommentThread } from "@/components/CommentThread";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/Spinner";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

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

type User = {
  id: number;
  full_name: string;
  role: "customer" | "agent" | "admin";
};

type SatisfactionRating = {
  rating: number;
  submitted_at: string;
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
  const { user } = useAuth();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [agents, setAgents] = useState<User[]>([]);
  const [selectedAssignee, setSelectedAssignee] = useState<string>("");
  const [assignError, setAssignError] = useState("");
  const [assignSuccess, setAssignSuccess] = useState("");
  const [isAssigning, setIsAssigning] = useState(false);

  const [satisfaction, setSatisfaction] = useState<SatisfactionRating | null>(null);
  const [ratingDraft, setRatingDraft] = useState<number>(5);
  const [ratingError, setRatingError] = useState("");
  const [ratingSuccess, setRatingSuccess] = useState("");
  const [isSubmittingRating, setIsSubmittingRating] = useState(false);

  const isAdmin = user?.role === "admin";
  const canRate = user?.role === "customer" && ticket?.status === "closed";

  const loadTicket = useCallback(
    async (isBackgroundRefresh = false) => {
      if (isBackgroundRefresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError("");
      try {
        const data = await api<Ticket>(`/tickets/${params.ticketId}`);
        setTicket(data);
        setSelectedAssignee(data.assignee_id ? String(data.assignee_id) : "");
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Could not load ticket.");
        }
      } finally {
        if (isBackgroundRefresh) {
          setIsRefreshing(false);
        } else {
          setIsLoading(false);
        }
      }
    },
    [params.ticketId]
  );

  useEffect(() => {
    // Initial fetch: loadTicket sets state only after the async request resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadTicket();
  }, [loadTicket]);

  useEffect(() => {
    if (!isAdmin) return;
    async function loadAgents() {
      try {
        const users = await api<User[]>("/admin/users");
        setAgents(users.filter((u) => u.role === "agent"));
      } catch (err) {
        setAssignError(
          err instanceof Error ? err.message : "Could not load agent list."
        );
      }
    }
    loadAgents();
  }, [isAdmin]);

  useEffect(() => {
    if (!ticket) return;
    const currentTicket = ticket;
    async function loadSatisfaction() {
      try {
        const data = await api<SatisfactionRating | null>(
          `/tickets/${currentTicket.id}/satisfaction`
        );
        if (data) {
          setSatisfaction(data);
          setRatingDraft(data.rating);
        }
      } catch {
        // Not critical for ticket rendering; avoid blocking page.
      }
    }
    loadSatisfaction();
  }, [ticket?.id]);

  async function handleAssignmentSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!ticket) return;
    setAssignError("");
    setAssignSuccess("");
    setIsAssigning(true);
    try {
      const assignee_id = selectedAssignee ? Number(selectedAssignee) : null;
      const updated = await api<Ticket>(`/admin/tickets/${ticket.id}/assignee`, {
        method: "PATCH",
        body: JSON.stringify({ assignee_id }),
      });
      setTicket(updated);
      setSelectedAssignee(updated.assignee_id ? String(updated.assignee_id) : "");
      setAssignSuccess(
        updated.assignee_id === null
          ? "Ticket unassigned successfully."
          : "Ticket assignment updated."
      );
    } catch (err) {
      setAssignError(
        err instanceof Error ? err.message : "Could not update assignment."
      );
    } finally {
      setIsAssigning(false);
    }
  }

  async function handleRatingSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!ticket) return;
    setRatingError("");
    setRatingSuccess("");
    setIsSubmittingRating(true);
    try {
      const saved = await api<SatisfactionRating>(`/tickets/${ticket.id}/satisfaction`, {
        method: "POST",
        body: JSON.stringify({ rating: ratingDraft }),
      });
      setSatisfaction(saved);
      setRatingSuccess("Thanks! Your feedback has been saved.");
      await loadTicket(true);
    } catch (err) {
      setRatingError(err instanceof Error ? err.message : "Could not save rating.");
    } finally {
      setIsSubmittingRating(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Spinner size="h-8 w-8" label="Loading ticket details…" />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load ticket"
        description={error}
        action={
          <Link className="text-sm font-medium text-brand underline" href="/tickets">
            Back to tickets
          </Link>
        }
      />
    );
  }

  if (!ticket) {
    return (
      <EmptyState
        title="Ticket not found"
        description="This ticket may have been removed or you may not have access to it."
        action={
          <Link className="text-sm font-medium text-brand underline" href="/tickets">
            Back to tickets
          </Link>
        }
      />
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

      {isAdmin && (
        <section
          className="space-y-4 rounded-lg border border-border bg-surface p-5"
          aria-labelledby="assignment-heading"
        >
          <div>
            <h2 id="assignment-heading" className="text-sm font-semibold uppercase tracking-wide text-muted">
              Assignment
            </h2>
            <p className="mt-1 text-sm text-muted">
              Assign or reassign this ticket to an available agent.
            </p>
          </div>

          <form className="space-y-3 sm:flex sm:items-end sm:gap-3 sm:space-y-0" onSubmit={handleAssignmentSubmit}>
            <div className="w-full sm:max-w-xs">
              <label htmlFor="assignee-select" className="mb-1 block text-sm font-medium">
                Assignee
              </label>
              <select
                id="assignee-select"
                value={selectedAssignee}
                onChange={(e) => setSelectedAssignee(e.target.value)}
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
              >
                <option value="">Unassigned</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={String(agent.id)}>
                    {agent.full_name} (#{agent.id})
                  </option>
                ))}
              </select>
            </div>

            <Button type="submit" disabled={isAssigning || isRefreshing}>
              {isAssigning ? "Saving..." : "Save assignment"}
            </Button>
          </form>

          {assignError && <p className="text-sm text-priority-urgent">{assignError}</p>}
          {assignSuccess && <p className="text-sm text-status-resolved">{assignSuccess}</p>}
        </section>
      )}

      {canRate && ticket && (
        <section
          className="space-y-4 rounded-lg border border-border bg-surface p-5"
          aria-labelledby="satisfaction-heading"
        >
          <div>
            <h2
              id="satisfaction-heading"
              className="text-sm font-semibold uppercase tracking-wide text-muted"
            >
              Satisfaction
            </h2>
            <p className="mt-1 text-sm text-muted">
              Rate your experience after this ticket was closed.
            </p>
          </div>

          <form className="space-y-3 sm:flex sm:items-end sm:gap-3 sm:space-y-0" onSubmit={handleRatingSubmit}>
            <div className="w-full sm:max-w-xs">
              <label htmlFor="rating-select" className="mb-1 block text-sm font-medium">
                Rating (1-5)
              </label>
              <select
                id="rating-select"
                value={String(ratingDraft)}
                onChange={(e) => setRatingDraft(Number(e.target.value))}
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
              >
                <option value="5">5 - Excellent</option>
                <option value="4">4 - Good</option>
                <option value="3">3 - Okay</option>
                <option value="2">2 - Poor</option>
                <option value="1">1 - Very poor</option>
              </select>
            </div>

            <Button type="submit" disabled={isSubmittingRating}>
              {isSubmittingRating ? "Saving..." : satisfaction ? "Update rating" : "Submit rating"}
            </Button>
          </form>

          {satisfaction && (
            <p className="text-sm text-muted">
              Current rating: {satisfaction.rating}/5, submitted on{" "}
              {formatDate(satisfaction.submitted_at)}.
            </p>
          )}
          {ratingError && <p className="text-sm text-priority-urgent">{ratingError}</p>}
          {ratingSuccess && <p className="text-sm text-status-resolved">{ratingSuccess}</p>}
        </section>
      )}

      <CommentThread ticketId={ticket.id} />
    </div>
  );
}