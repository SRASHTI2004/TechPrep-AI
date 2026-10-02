// Thin fetch wrapper: base URL, bearer token, JSON, typed errors.

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";
const TOKEN_KEY = "techprep.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const tokenStore = {
  get: (): string | null => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// Called on 401 so the app can drop the session and redirect to /login.
let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

export function apiUrl(path: string): string {
  return `${BASE_URL}/api/v1${path}`;
}

export function authHeaders(): Record<string, string> {
  const token = tokenStore.get();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function messageFrom(status: number, body: unknown): string {
  if (status === 429) return "Too many requests. Please wait a moment and try again.";
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return `Request failed (${status})`;
}

export async function ensureOk(res: Response): Promise<Response> {
  if (res.ok) return res;
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON error body */
  }
  if (res.status === 401) onUnauthorized();
  throw new ApiError(res.status, messageFrom(res.status, body), body);
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders(), ...(init.headers as object) };
  if (init.body && !(init.body instanceof FormData) && !(init.body instanceof URLSearchParams)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await ensureOk(await fetch(apiUrl(path), { ...init, headers }));
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
