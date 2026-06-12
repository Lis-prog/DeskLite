import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

/** Generic surface card. Use instead of one-off border/bg combos. */
export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-border bg-surface shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  children,
  className = "",
}: CardProps) {
  return (
    <div className={`border-b border-border px-5 py-4 ${className}`}>
      {children}
    </div>
  );
}

export function CardBody({ children, className = "" }: CardProps) {
  return <div className={`px-5 py-4 ${className}`}>{children}</div>;
}