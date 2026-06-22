"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/Spinner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";

type CommentAuthor = {
  id: number;
  full_name: string;
};

type Comment = {
  id: number;
  ticket_id: number;
  author_id: number;
  author: CommentAuthor;
  body: string;
  created_at: string;
};

function formatRelative(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(iso).toLocaleDateString("en", {
    month: "short",
    day: "numeric",
  });
}

function Avatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0] ?? "")
    .join("")
    .toUpperCase();

  return (
    <span
      aria-hidden="true"
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-light text-xs font-semibold text-brand"
    >
      {initials}
    </span>
  );
}

type CommentThreadProps = {
  ticketId: number;
};

export function CommentThread({ ticketId }: CommentThreadProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [body, setBody] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await api<Comment[]>(`/tickets/${ticketId}/comments`);
        setComments(data);
      } catch (err) {
        setLoadError(
          err instanceof Error ? err.message : "Could not load comments."
        );
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [ticketId]);

  // Scroll to bottom whenever new comments appear
  useEffect(() => {
    if (comments.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [comments.length]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;

    setSubmitError("");
    setIsSubmitting(true);
    try {
      const newComment = await api<Comment>(`/tickets/${ticketId}/comments`, {
        method: "POST",
        body: JSON.stringify({ body: body.trim() }),
      });
      setComments((prev) => [...prev, newComment]);
      setBody("");
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Could not post comment."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="space-y-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
        Comments{comments.length > 0 ? ` (${comments.length})` : ""}
      </h2>

      {/* Comment list */}
      {isLoading && (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface p-5 text-sm text-muted">
          <Spinner size="h-4 w-4" />
          <span>Loading comments…</span>
        </div>
      )}

      {!isLoading && loadError && (
        <ErrorState title="Could not load comments" description={loadError} />
      )}

      {!isLoading && !loadError && comments.length === 0 && (
        <EmptyState
          title="No comments yet"
          description="Be the first to reply."
        />
      )}

      {!isLoading && !loadError && comments.length > 0 && (
        <div className="rounded-lg border border-border bg-surface">
          <ul className="divide-y divide-border">
            {comments.map((comment) => (
              <li key={comment.id} className="flex gap-3 p-4">
                <Avatar name={comment.author.full_name} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-sm font-medium">
                      {comment.author.full_name}
                    </span>
                    <time
                      dateTime={comment.created_at}
                      className="text-xs text-muted"
                    >
                      {formatRelative(comment.created_at)}
                    </time>
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-sm">
                    {comment.body}
                  </p>
                </div>
              </li>
            ))}
          </ul>
          <div ref={bottomRef} />
        </div>
      )}

      {/* Reply form */}
      <form onSubmit={handleSubmit} className="space-y-2">
        <label htmlFor="comment-body" className="sr-only">
          Add a comment
        </label>
        <textarea
          id="comment-body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a comment…"
          rows={3}
          maxLength={10_000}
          required
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand focus:ring-offset-2"
        />

        {submitError && (
          <p className="text-sm text-priority-urgent">{submitError}</p>
        )}

        <div className="flex justify-end">
          <Button type="submit" disabled={isSubmitting || !body.trim()}>
            {isSubmitting ? "Posting…" : "Post comment"}
          </Button>
        </div>
      </form>
    </section>
  );
}
