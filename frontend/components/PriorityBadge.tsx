type TicketPriority = "low" | "medium" | "high" | "urgent";

const styles: Record<TicketPriority, string> = {
  low: "bg-priority-low/10 text-priority-low",
  medium: "bg-priority-medium/10 text-priority-medium",
  high: "bg-priority-high/10 text-priority-high",
  urgent: "bg-priority-urgent/10 text-priority-urgent",
};

const labels: Record<TicketPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  urgent: "Urgent",
};

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[priority]}`}
    >
      {labels[priority]}
    </span>
  );
}