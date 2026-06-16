import type { ReactNode } from "react";

interface ErrorStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function ErrorState({ title, description, action }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-surface px-6 py-16 text-center">
      {/* Icon - error icon */}
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-priority-urgent/10">
        <svg
          className="h-6 w-6 text-priority-urgent"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
          />
        </svg>
      </div>

      <p className="text-sm font-medium text-slate-900">{title}</p>
      {description && (
        <p className="mt-1 text-sm text-muted">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}