// Same-origin client for the Next.js BFF (`/api/*`). The browser never sees the
// JWT — the route handlers attach it from an httpOnly cookie (see ADR-0011).

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(res.status, detail || "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
