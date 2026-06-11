import type { Config } from "tailwindcss";

// DeskLite design tokens — Egzona owns these; everyone uses them (no raw hex in components).
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#4f46e5",
          dark: "#4338ca",
          light: "#eef2ff",
        },
        surface: "#ffffff",
        muted: "#6b7280",
        border: "#e5e7eb",
        status: {
          open: "#3b82f6",
          progress: "#f59e0b",
          resolved: "#10b981",
          closed: "#6b7280",
        },
        priority: {
          low: "#9ca3af",
          medium: "#3b82f6",
          high: "#f59e0b",
          urgent: "#ef4444",
        },
      },
    },
  },
  plugins: [],
};

export default config;
