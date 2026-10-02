import { readSse } from "../lib/sse";
import { apiUrl, authHeaders, ensureOk, request } from "./client";
import type {
  ChatDone,
  ChatMeta,
  Citation,
  Conversation,
  ConversationDetail,
  DocumentItem,
  DocumentList,
  TokenResponse,
  User,
} from "./types";

export const authApi = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password }),
    }),
  me: () => request<User>("/auth/me"),
};

export const documentsApi = {
  list: () => request<DocumentList>("/documents?limit=200"),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<DocumentItem>("/documents", { method: "POST", body });
  },
  remove: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  reingest: (id: string) => request<DocumentItem>(`/documents/${id}/reingest`, { method: "POST" }),
};

export const conversationsApi = {
  list: () => request<Conversation[]>("/conversations"),
  get: (id: string) => request<ConversationDetail>(`/conversations/${id}`),
  remove: (id: string) => request<void>(`/conversations/${id}`, { method: "DELETE" }),
  feedback: (messageId: string, value: 1 | -1) =>
    request<void>(`/messages/${messageId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ value }),
    }),
};

export interface StreamHandlers {
  onMeta?: (meta: ChatMeta) => void;
  onSources?: (sources: Citation[]) => void;
  onToken?: (text: string) => void;
  onDone?: (done: ChatDone) => void;
  onError?: (detail: string) => void;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
  document_ids?: string[] | null;
}

/** POST /chat/stream and dispatch SSE events to handlers. */
export async function streamChat(
  body: ChatRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await ensureOk(
    await fetch(apiUrl("/chat/stream"), {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    }),
  );
  for await (const ev of readSse(res, signal)) {
    const data = JSON.parse(ev.data);
    switch (ev.event) {
      case "meta":
        handlers.onMeta?.(data as ChatMeta);
        break;
      case "sources":
        handlers.onSources?.(data as Citation[]);
        break;
      case "token":
        handlers.onToken?.((data as { text: string }).text);
        break;
      case "done":
        handlers.onDone?.(data as ChatDone);
        break;
      case "error":
        handlers.onError?.((data as { detail: string }).detail);
        break;
    }
  }
}
