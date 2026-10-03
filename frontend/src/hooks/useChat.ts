import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";
import { conversationsApi, streamChat } from "../api/endpoints";
import type { AnswerMode, Citation, Latency, StoredMessage } from "../api/types";

export interface UiMessage {
  key: string;
  id?: string; // server id once known (needed for feedback)
  role: "user" | "assistant";
  content: string;
  sources: Citation[]; // every source the model was given for this answer
  cited: number[]; // the source numbers the answer cites, in order of first citation
  mode?: AnswerMode;
  answered?: boolean;
  streaming?: boolean;
  status?: string; // progress text while a long summary is prepared
  stopped?: boolean; // the user pressed "Stop generating"
  error?: string;
  feedback?: 1 | -1 | null;
  latency?: Latency;
  rewrittenQuestion?: string | null;
  provider?: string | null;
}

export interface SendOptions {
  mode?: "auto" | AnswerMode;
}

let keySeq = 0;
const nextKey = () => `m${++keySeq}`;

export function fromStored(m: StoredMessage): UiMessage {
  const citations = m.citations ?? [];
  return {
    key: m.id,
    id: m.id,
    role: m.role,
    content: m.content,
    // Newer messages store every source with a `cited` flag; older ones only their citations.
    sources: m.sources?.length ? m.sources : citations,
    cited: citations.map((c) => c.n),
    mode: m.mode ?? undefined,
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
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [reloadCount, setReloadCount] = useState(0);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  // Set when *we* just created this conversation, so we don't refetch it mid-stream.
  const createdHereRef = useRef<string | null>(null);

  useEffect(() => {
    setHistoryError(null);
    if (!conversationId) {
      setMessages([]);
      return;
    }
    if (createdHereRef.current === conversationId) return;
    let cancelled = false;
    setLoadingHistory(true);
    setMessages([]);
    conversationsApi
      .get(conversationId)
      .then((c) => !cancelled && setMessages(c.messages.map(fromStored)))
      .catch((err) => {
        if (cancelled) return;
        setMessages([]);
        setHistoryError(err instanceof ApiError ? err.message : "Connection lost. Please try again.");
      })
      .finally(() => !cancelled && setLoadingHistory(false));
    return () => {
      cancelled = true;
    };
  }, [conversationId, reloadCount]);

  const reloadHistory = useCallback(() => setReloadCount((n) => n + 1), []);

  useEffect(() => () => abortRef.current?.abort(), []);

  const patchLast = (patch: (m: UiMessage) => UiMessage) =>
    setMessages((ms) => (ms.length ? [...ms.slice(0, -1), patch(ms[ms.length - 1]!)] : ms));

  const send = useCallback(
    async (text: string, documentIds: string[] | null, options: SendOptions = {}) => {
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
          {
            message: text,
            conversation_id: conversationId,
            document_ids: documentIds,
            mode: options.mode ?? "auto",
          },
          {
            onMeta: (meta) => {
              if (!conversationId) {
                createdHereRef.current = meta.conversation_id;
                onConversationCreated(meta.conversation_id);
              }
              patchLast((m) => ({ ...m, rewrittenQuestion: meta.rewritten_question, mode: meta.mode }));
            },
            onSources: (sources) => patchLast((m) => ({ ...m, sources })),
            onStatus: (status) => patchLast((m) => ({ ...m, status })),
            onToken: (t) => patchLast((m) => ({ ...m, status: undefined, content: m.content + t })),
            onDone: (done) =>
              patchLast((m) => {
                const cited = done.citations.map((c) => c.n);
                return {
                  ...m,
                  id: done.message_id,
                  // The stored answer can differ from the streamed text (normalized citations).
                  content: done.answer ?? m.content,
                  streaming: false,
                  status: undefined,
                  answered: done.answered,
                  mode: done.mode ?? m.mode,
                  cited,
                  sources: m.sources.map((s) => ({ ...s, cited: cited.includes(s.n) })),
                  latency: done.latency,
                  provider: done.provider,
                };
              }),
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
        // Still "streaming" here means the answer never finished: stopped or cut off.
        const stopped = controller.signal.aborted;
        patchLast((m) =>
          m.streaming ? { ...m, streaming: false, status: undefined, stopped } : m,
        );
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

  return { messages, loadingHistory, historyError, reloadHistory, busy, send, stop, setFeedback };
}
