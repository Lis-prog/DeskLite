import type { Metadata } from "next";

import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "DeskLite",
  description: "Internal support ticket system",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
    apple: [{ url: "/apple-icon.svg", type: "image/svg+xml" }],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-brand focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          >
            Skip to main content
          </a>
          <Nav />
          <main
            id="main-content"
            tabIndex={-1}
            className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10"
          >
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
