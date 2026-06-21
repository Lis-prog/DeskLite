"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type State = "loading" | "ok" | "error";

export function ApiStatus() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    fetch(`${API}/api/v1/health`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("bad status"))))
      .then(() => setState("ok"))
      .catch(() => setState("error"));
  }, []);

  if (state === "loading") {
    return <span className="text-sm text-muted">Checking API…</span>;
  }
  if (state === "ok") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-status-resolved/10 px-3 py-1 text-sm font-medium text-status-resolved">
        <span className="h-2 w-2 rounded-full bg-status-resolved" />
        API reachable
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-priority-urgent/10 px-3 py-1 text-sm font-medium text-priority-urgent">
      <span className="h-2 w-2 rounded-full bg-priority-urgent" />
      API unreachable — is the backend running?
    </span>
  );
}
