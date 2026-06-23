export function OverdueBadge() {
  return (
    <span
      className="inline-flex items-center rounded-full bg-danger/10 px-2.5 py-0.5 text-xs font-medium text-danger"
      title="Past its SLA deadline"
    >
      Overdue
    </span>
  );
}
