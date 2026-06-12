import { PriorityBadge } from "@/components/PriorityBadge";
import { StatusBadge } from "@/components/StatusBadge";

const tickets = [
  {
    id: "DL-101",
    title: "Cannot access internal dashboard",
    priority: "high",
    status: "open",
  },
  {
    id: "DL-102",
    title: "Email notifications not received",
    priority: "medium",
    status: "in_progress",
  },
  {
    id: "DL-103",
    title: "Request for new laptop setup",
    priority: "low",
    status: "resolved",
  },
] as const;

export default function TicketsPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold">Tickets</h1>
        <p className="mt-2 text-muted">
          View and track support requests in one place.
        </p>
      </section>

      <div className="rounded-lg border border-border bg-surface">
        {tickets.map((ticket) => (
          <div
            key={ticket.id}
            className="flex items-center justify-between border-b border-border p-4 last:border-b-0"
          >
            <div>
              <p className="text-sm text-muted">{ticket.id}</p>
              <h2 className="font-semibold">{ticket.title}</h2>
            </div>

            <div className="flex gap-2">
              <PriorityBadge priority={ticket.priority} />
              <StatusBadge status={ticket.status} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}