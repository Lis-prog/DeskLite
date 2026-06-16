import { ApiStatus } from "@/components/ApiStatus";
import { StatusBadge } from "@/components/StatusBadge";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section> n
        <h1 className="text-2xl font-bold">DeskLite is running 🎉</h1>
        <p className="mt-2 text-muted">
          Sprint 0 skeleton. The foundation is up — start building your tickets on top of it.
        </p>
      </section>

      <section className="rounded-lg border border-border bg-surface p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          Backend connection
        </h2>
        <div className="mt-3">
          <ApiStatus />
        </div>
      </section>

      <section className="rounded-lg border border-border bg-surface p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          Design tokens preview
        </h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <StatusBadge status="open" />
          <StatusBadge status="in_progress" />
          <StatusBadge status="resolved" />
          <StatusBadge status="closed" />
        </div>
      </section>

      <section className="text-sm text-muted">
        <p>
          API docs:{" "}
          <a className="text-brand underline" href="http://localhost:8000/docs">
            localhost:8000/docs
          </a>
        </p>
      </section>
    </div>
  );
}
