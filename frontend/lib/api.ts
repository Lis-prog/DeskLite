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
  return fetch(`${BASE}${API_PREFIX}${path}`, {
    credentials: "include", // send httpOnly auth cookie
    headers: {
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
