import type { Metadata } from "next";

import "./globals.css";
import { LogoutButton } from "@/components/LogoutButton"; 

export const metadata: Metadata = {
  title: "DeskLite",
  description: "Internal support ticket system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-border bg-surface">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
            <span className="text-lg font-semibold text-brand">DeskLite</span>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted">Internal Support</span>
            <LogoutButton />
          </div>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
