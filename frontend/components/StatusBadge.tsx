type TicketStatus = "open" | "in_progress" | "resolved" | "closed";

const styles: Record<TicketStatus, string> = {
  open: "bg-status-open/10 text-status-open",
  in_progress: "bg-status-progress/10 text-status-progress",
  resolved: "bg-status-resolved/10 text-status-resolved",
  closed: "bg-status-closed/10 text-status-closed",
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${styles[status]}`}
    >
      {status.replace("_", " ")}
    </span>
  );
}
