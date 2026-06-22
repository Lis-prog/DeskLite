// Typed API client — ALL backend calls go through here.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_PREFIX = "/api/v1";
const REFRESH_PATH = "/auth/refresh";

let refreshInFlight: Promise<boolean> | null = null;

function formatApiError(body: { detail?: string | { msg: string }[] }): string {
  const { detail } = body;
  if (!detail) {
    return "Request failed";
  }
  if (typeof detail === "string") {
    return detail;
  }
  return detail.map((item) => item.msg).join(", ");
}

function request(path: string, init?: RequestInit): Promise<Response> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  return fetch(`${BASE}${API_PREFIX}${path}`, {
    credentials: "include", // send httpOnly auth cookie
    headers: isFormData
      ? { ...(init?.headers ?? {}) }
      : {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
    ...init,
  });
}

function shouldTryRefresh(path: string, init?: RequestInit): boolean {
  // Avoid loops and noisy retries on endpoints that intentionally return 401.
  if (path === REFRESH_PATH || path === "/auth/login" || path === "/auth/register") {
    return false;
  }

  const method = init?.method?.toUpperCase() ?? "GET";
  if (method === "OPTIONS") {
    return false;
  }

  return true;
}

async function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const res = await request(REFRESH_PATH, { method: "POST" });
      return res.ok;
    })().finally(() => {
      refreshInFlight = null;
    });
  }

  return refreshInFlight;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let res = await request(path, init);

  if (
    res.status === 401 &&
    shouldTryRefresh(path, init) &&
    (await refreshSession())
  ) {
    // Retry once after rotating auth cookies via /auth/refresh.
    res = await request(path, init);
  }

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      detail?: string | { msg: string }[];
    };
    throw new Error(formatApiError(body) || `Request failed with ${res.status}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

// ── Metrics ──────────────────────────────────────────────────────────────
// Types mirror the backend response models in app/schemas/metrics.py.

export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type TicketPriority = "low" | "medium" | "high" | "urgent";

export type TicketMetrics = {
  total: number;
  by_status: Record<TicketStatus, number>;
  by_priority: Record<TicketPriority, number>;
  unassigned: number;
};

export type AgentWorkload = {
  agent_id: number;
  full_name: string;
  email: string;
  active_ticket_count: number;
};

export type ResolutionTime = {
  resolved_count: number;
  average_seconds: number | null;
  median_seconds: number | null;
};

/** GET /metrics/tickets — counts grouped by status and priority (role-scoped). */
export function getTicketMetrics(): Promise<TicketMetrics> {
  return api<TicketMetrics>("/metrics/tickets");
}

/** GET /metrics/agents/workload — active ticket load per agent (admin only). */
export function getAgentWorkload(): Promise<AgentWorkload[]> {
  return api<AgentWorkload[]>("/metrics/agents/workload");
}

/** GET /metrics/resolution-time — average/median creation-to-resolution time. */
export function getResolutionTime(): Promise<ResolutionTime> {
  return api<ResolutionTime>("/metrics/resolution-time");
}
