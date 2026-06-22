"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PriorityBadge } from "@/components/PriorityBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

type TicketPriority = "low" | "medium" | "high" | "urgent";

type TicketRead = {
  id: number;
  title: string;
  description: string;
  status: "open" | "in_progress" | "resolved" | "closed";
  priority: TicketPriority;
  requester_id: number;
  assignee_id: number | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
};

const PRIORITIES: { value: TicketPriority; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

const inputClassName =
  "mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand";

export default function NewTicketPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("medium");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdTicket, setCreatedTicket] = useState<TicketRead | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setIsSubmitting(true);

    try {
      const ticket = await api<TicketRead>("/tickets", {
        method: "POST",
        body: JSON.stringify({ title, description, priority }),
      });
      setCreatedTicket(ticket);
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Could not connect to the server."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (createdTicket) {
    return (
      <div className="mx-auto max-w-md">
        <div className="rounded-lg border border-border bg-surface p-6 shadow-sm">
          <h1 className="text-2xl font-bold">Ticket submitted</h1>
          <p className="mt-2 text-sm text-muted">
            Your request was created and is now open for the support team.
          </p>

          <div className="mt-6 space-y-3 rounded-md border border-border p-4">
            <p className="text-sm text-muted">Ticket #{createdTicket.id}</p>
            <p className="font-semibold">{createdTicket.title}</p>
            {createdTicket.description && (
              <p className="text-sm text-muted">{createdTicket.description}</p>
            )}
            <div className="flex gap-2">
              <PriorityBadge priority={createdTicket.priority} />
              <StatusBadge status={createdTicket.status} />
            </div>
          </div>

          <div className="mt-6 flex flex-col gap-3">
            <Button
              type="button"
              className="w-full"
              onClick={() => router.push("/tickets")}
            >
              View tickets
            </Button>
            <button
              type="button"
              className="text-sm text-brand underline"
              onClick={() => {
                setCreatedTicket(null);
                setTitle("");
                setDescription("");
                setPriority("medium");
              }}
            >
              Create another ticket
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="rounded-lg border border-border bg-surface p-6 shadow-sm">
        <h1 className="text-2xl font-bold">New ticket</h1>
        <p className="mt-2 text-sm text-muted">
          Describe your issue and we&apos;ll track it from here.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <Input
            id="title"
            label="Subject"
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Short summary of the problem"
            required
            maxLength={200}
          />

          <div>
            <label htmlFor="description" className="text-sm font-medium">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What happened? Include steps to reproduce if you can."
              rows={5}
              maxLength={20000}
              className={inputClassName}
            />
          </div>

          <div>
            <label htmlFor="priority" className="text-sm font-medium">
              Priority
            </label>
            <select
              id="priority"
              value={priority}
              onChange={(event) => setPriority(event.target.value as TicketPriority)}
              className={inputClassName}
            >
              {PRIORITIES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {message && (
            <p className="text-sm text-muted">
              {message}
              {message.includes("Not authenticated") && (
                <>
                  {" "}
                  <Link href="/login" className="text-brand underline">
                    Log in
                  </Link>
                </>
              )}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Submitting..." : "Submit ticket"}
          </Button>
        </form>

        <p className="mt-4 text-sm text-muted">
          <Link href="/tickets" className="text-brand underline">
            Back to tickets
          </Link>
        </p>
      </div>
    </div>
  );
}
