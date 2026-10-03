// Mirrors backend/app/schemas/*.py. Keep in sync when the API changes.

export type Role = "user" | "admin";

export interface User {
  id: string;
  email: string;
  role: Role;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface DocumentItem {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: DocumentStatus;
  error: string | null;
  num_pages: number | null;
  num_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentList {
  items: DocumentItem[];
  total: number;
}

export interface Citation {
  n: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  page: number | null;
  section: string | null;
  snippet: string;
  score: number;
  /** Set once the answer is final: did the answer cite this source? */
  cited?: boolean;
}

export type AnswerMode = "qa" | "summary";

export interface Latency {
  retrieval_ms: number;
  generation_ms: number;
  total_ms: number;
}

export interface ChatDone {
  conversation_id: string;
  message_id: string;
  /** The final stored answer (may differ slightly from the streamed tokens). */
  answer?: string;
  answered: boolean;
  mode?: AnswerMode;
  citations: Citation[];
  invalid_citations: number[];
  rewritten_question: string | null;
  provider: string | null;
  model: string | null;
  latency: Latency;
}

export interface ChatMeta {
  conversation_id: string;
  user_message_id: string;
  rewritten_question: string | null;
  mode?: AnswerMode;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  /** Every source the model was given, with `cited` flags (older messages may lack it). */
  sources?: Citation[];
  mode?: AnswerMode | null;
  answered: boolean | null;
  feedback: 1 | -1 | null;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: StoredMessage[];
}
