"use client";

import { useState } from "react";

import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import type { UserRole } from "@/lib/auth-context";

type TicketStatus = "open" | "in_progress" | "resolved" | "closed";

// Mirrors the backend lifecycle (open → in_progress → resolved → closed).
// The API stays authoritative; this only decides which control we offer.
const NEXT_STATUS: Partial<Record<TicketStatus, TicketStatus>> = {
  open: "in_progress",
  in_progress: "resolved",
  resolved: "closed",
};

const NEXT_ACTION_LABEL: Record<TicketStatus, string> = {
  open: "Reopen ticket",
  in_progress: "Start progress",
  resolved: "Mark resolved",
  closed: "Close ticket",
};

type TicketStatusControlsProps = {
  ticketId: number;
  status: TicketStatus;
  assigneeId: number | null;
  userRole: UserRole;
  userId: number;
  onUpdated: () => void | Promise<void>;
};

export function TicketStatusControls({
  ticketId,
  status,
  assigneeId,
  userRole,
  userId,
  onUpdated,
}: TicketStatusControlsProps) {
  const [error, setError] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  // Same rule the API enforces: only an admin or the assigned agent may
  // advance status. Customers and other agents never see these controls,
  // but the backend remains the real security boundary.
  const canChangeStatus =
    userRole === "admin" || (userRole === "agent" && assigneeId === userId);

  if (!canChangeStatus) {
    return null;
  }

  const nextStatus = NEXT_STATUS[status];

  async function handleAdvance() {
    if (!nextStatus) {
      return;
    }
    setError("");
    setIsUpdating(true);
    try {
      await api(`/tickets/${ticketId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      await onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update status.");
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <section
      className="space-y-4 rounded-lg border border-border bg-surface p-5"
      aria-labelledby="status-controls-heading"
    >
      <div>
        <h2
          id="status-controls-heading"
          className="text-sm font-semibold uppercase tracking-wide text-muted"
        >
          Status
        </h2>
        <p className="mt-1 text-sm text-muted">
          Advance this ticket through its lifecycle.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-muted">Current:</span>
        <StatusBadge status={status} />
      </div>

      {nextStatus ? (
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" onClick={handleAdvance} disabled={isUpdating}>
            {isUpdating ? "Updating..." : NEXT_ACTION_LABEL[nextStatus]}
          </Button>
          <span className="text-sm text-muted">
            Moves status to{" "}
            <span className="font-medium capitalize">
              {nextStatus.replace("_", " ")}
            </span>
            .
          </span>
        </div>
      ) : (
        <p className="text-sm text-muted">
          This ticket is closed. No further status changes are available.
        </p>
      )}

      {error && <p className="text-sm text-priority-urgent">{error}</p>}
    </section>
  );
}
