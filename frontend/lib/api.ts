// Typed API client — ALL backend calls go through here.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    credentials: "include", // send httpOnly auth cookie
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

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
