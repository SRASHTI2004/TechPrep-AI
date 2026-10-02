import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";
import { conversationsApi, streamChat } from "../api/endpoints";
import type { Citation, Latency, StoredMessage } from "../api/types";

export interface UiMessage {
  key: string;
  id?: string; // server id once known (needed for feedback)
  role: "user" | "assistant";
  content: string;
  sources: Citation[]; // what the model was given (live) or what it cited (history)
  cited: number[];
  answered?: boolean;
  streaming?: boolean;
  error?: string;
  feedback?: 1 | -1 | null;
  latency?: Latency;
  rewrittenQuestion?: string | null;
  provider?: string | null;
}

let keySeq = 0;
const nextKey = () => `m${++keySeq}`;

export function fromStored(m: StoredMessage): UiMessage {
  return {
    key: m.id,
    id: m.id,
    role: m.role,
    content: m.content,
    sources: m.citations ?? [],
    cited: (m.citations ?? []).map((c) => c.n),
    answered: m.answered ?? undefined,
    feedback: m.feedback,
  };
}

/**
 * Chat state for one conversation. `onConversationCreated` fires when the server assigns an
 * id to a brand-new conversation (the page puts it in the URL).
 */
export function useChat(
  conversationId: string | null,
  onConversationCreated: (id: string) => void,
) {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  // Set when *we* just created this conversation, so we don't refetch it mid-stream.
  const createdHereRef = useRef<string | null>(null);

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    if (createdHereRef.current === conversationId) return;
    let cancelled = false;
    setLoadingHistory(true);
    conversationsApi
      .get(conversationId)
      .then((c) => !cancelled && setMessages(c.messages.map(fromStored)))
      .catch(() => !cancelled && setMessages([]))
      .finally(() => !cancelled && setLoadingHistory(false));
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const patchLast = (patch: (m: UiMessage) => UiMessage) =>
    setMessages((ms) => (ms.length ? [...ms.slice(0, -1), patch(ms[ms.length - 1]!)] : ms));

  const send = useCallback(
    async (text: string, documentIds: string[] | null) => {
      if (busy || !text.trim()) return;
      setBusy(true);
      const controller = new AbortController();
      abortRef.current = controller;
      setMessages((ms) => [
        ...ms,
        { key: nextKey(), role: "user", content: text, sources: [], cited: [] },
        { key: nextKey(), role: "assistant", content: "", sources: [], cited: [], streaming: true },
      ]);

      try {
        await streamChat(
          { message: text, conversation_id: conversationId, document_ids: documentIds },
          {
            onMeta: (meta) => {
              if (!conversationId) {
                createdHereRef.current = meta.conversation_id;
                onConversationCreated(meta.conversation_id);
              }
              patchLast((m) => ({ ...m, rewrittenQuestion: meta.rewritten_question }));
            },
            onSources: (sources) => patchLast((m) => ({ ...m, sources })),
            onToken: (t) => patchLast((m) => ({ ...m, content: m.content + t })),
            onDone: (done) =>
              patchLast((m) => ({
                ...m,
                id: done.message_id,
                streaming: false,
                answered: done.answered,
                cited: done.citations.map((c) => c.n),
                latency: done.latency,
                provider: done.provider,
              })),
            onError: (detail) => patchLast((m) => ({ ...m, streaming: false, error: detail })),
          },
          controller.signal,
        );
      } catch (err) {
        if (!controller.signal.aborted) {
          const message =
            err instanceof ApiError ? err.message : "Connection lost. Please try again.";
          patchLast((m) => ({ ...m, streaming: false, error: message }));
        }
      } finally {
        patchLast((m) => (m.streaming ? { ...m, streaming: false } : m));
        setBusy(false);
        queryClient.invalidateQueries({ queryKey: ["conversations"] });
      }
    },
    [busy, conversationId, onConversationCreated, queryClient],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const setFeedback = useCallback(async (messageId: string, value: 1 | -1) => {
    await conversationsApi.feedback(messageId, value);
    setMessages((ms) => ms.map((m) => (m.id === messageId ? { ...m, feedback: value } : m)));
  }, []);

  return { messages, loadingHistory, busy, send, stop, setFeedback };
}
