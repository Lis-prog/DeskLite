import type { ButtonHTMLAttributes } from "react";

// Shared button — use this instead of one-off styles (see CONTRIBUTING.md).
export function Button({
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`rounded-md bg-brand px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}
