import Link from "next/link";

import { ApiStatus } from "@/components/ApiStatus";

const FEATURES = [
  {
    title: "Raise tickets",
    description: "Customers submit issues and follow every update in one place.",
  },
  {
    title: "Work the queue",
    description: "Agents pick up, assign, and move tickets through their lifecycle.",
  },
  {
    title: "Track everything",
    description: "Managers watch volume, workload, and resolution time live.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      <section className="rounded-lg border border-border bg-surface p-8 text-center sm:p-12">
        <h1 className="text-3xl font-bold sm:text-4xl">
          Support tickets, without the bloat
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-muted">
          DeskLite is a lightweight internal help desk — raise tickets, work them
          through their lifecycle, and track it all with role-based access.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/register"
            className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          >
            Get started
          </Link>
          <Link
            href="/login"
            className="rounded-md border border-border px-4 py-2 text-sm font-medium transition hover:bg-brand-light focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          >
            Sign in
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {FEATURES.map((feature) => (
          <div
            key={feature.title}
            className="rounded-lg border border-border bg-surface p-5"
          >
            <h2 className="text-sm font-semibold">{feature.title}</h2>
            <p className="mt-1 text-sm text-muted">{feature.description}</p>
          </div>
        ))}
      </section>

      <section className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-5 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          System status
        </h2>
        <ApiStatus />
      </section>
    </div>
  );
}
