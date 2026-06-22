import type { ReactNode } from "react";

type AlertVariant = "error" | "success" | "info";

interface AlertProps {
  variant?: AlertVariant;
  children: ReactNode;
}

const VARIANT_CLASSES: Record<AlertVariant, string> = {
  error: "border-red-200 bg-red-50 text-red-700",
  success: "border-green-200 bg-green-50 text-green-700",
  info: "border-border bg-surface text-muted",
};

/**
 * Compact inline message for form submission feedback (errors, success).
 * For full-page data-loading failures use `ErrorState` instead.
 */
export function Alert({ variant = "info", children }: AlertProps) {
  return (
    <p
      role={variant === "error" ? "alert" : "status"}
      className={`rounded-md border px-3 py-2 text-sm ${VARIANT_CLASSES[variant]}`}
    >
      {children}
    </p>
  );
}
