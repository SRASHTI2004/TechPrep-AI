import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { conversationsApi, documentsApi } from "../api/endpoints";
import MessageBubble from "../components/MessageBubble";
import SourcesPanel from "../components/SourcesPanel";
import { useChat } from "../hooks/useChat";

const SUGGESTIONS = [
  "What are the disadvantages of sharding?",
  "When should I use a CDN, and push vs pull?",
  "How does the 0-1 knapsack DP work?",
  "Explain the prefix function in KMP.",
];

export default function ChatPage() {
  const { conversationId = null } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [scope, setScope] = useState<string[]>([]); // [] = all documents
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const onCreated = useCallback(
    (id: string) => navigate(`/chat/${id}`, { replace: true }),
    [navigate],
  );
  const { messages, loadingHistory, busy, send, stop, setFeedback } = useChat(
    conversationId,
    onCreated,
  );

  const conversations = useQuery({ queryKey: ["conversations"], queryFn: conversationsApi.list });
  const documents = useQuery({ queryKey: ["documents"], queryFn: documentsApi.list });
  const readyDocs = (documents.data?.items ?? []).filter((d) => d.status === "ready");

  const deleteConv = useMutation({
    mutationFn: conversationsApi.remove,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (id === conversationId) navigate("/chat");
    },
  });

  // The sources panel follows the selected assistant message (default: the latest one).
  const assistantMessages = messages.filter((m) => m.role === "assistant");
  const selected = useMemo(
    () =>
      assistantMessages.find((m) => m.key === selectedKey) ??
      assistantMessages[assistantMessages.length - 1],
    [assistantMessages, selectedKey],
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  useEffect(() => {
    setSelectedKey(null);
    setActiveCitation(null);
  }, [conversationId]);

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setSelectedKey(null);
    setActiveCitation(null);
    void send(text, scope.length ? scope : null);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) submit();
  }

  const noDocs = documents.isSuccess && readyDocs.length === 0;

  return (
    <div className="chat-layout">
      <aside className="conversations">
        <button className="primary block" onClick={() => navigate("/chat")}>
          + New chat
        </button>
        <ul>
          {(conversations.data ?? []).map((c) => (
            <li key={c.id} className={c.id === conversationId ? "active" : ""}>
              <Link to={`/chat/${c.id}`} title={c.title}>
                {c.title}
              </Link>
              <button
                className="ghost icon"
                aria-label={`Delete conversation ${c.title}`}
                onClick={() => deleteConv.mutate(c.id)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="chat">
        <div className="chat-toolbar">
          <details className="scope">
            <summary>
              Search in: {scope.length ? `${scope.length} selected document(s)` : "all documents"}
            </summary>
            <div className="scope-menu">
              {readyDocs.length === 0 && <p className="muted small">No ready documents.</p>}
              {readyDocs.map((d) => (
                <label key={d.id}>
                  <input
                    type="checkbox"
                    checked={scope.includes(d.id)}
                    onChange={(e) =>
                      setScope((s) => (e.target.checked ? [...s, d.id] : s.filter((x) => x !== d.id)))
                    }
                  />
                  {d.filename}
                </label>
              ))}
              {scope.length > 0 && (
                <button className="ghost" onClick={() => setScope([])}>
                  Clear (search all)
                </button>
              )}
            </div>
          </details>
        </div>

        <div className="messages" aria-live="polite">
          {loadingHistory && <p className="muted center">Loading conversation…</p>}
          {!loadingHistory && messages.length === 0 && (
            <div className="welcome">
              <h2>Ask your notes anything</h2>
              {noDocs ? (
                <p className="muted">
                  You have no documents yet. <Link to="/documents">Upload notes or PDFs</Link> to
                  get started.
                </p>
              ) : (
                <>
                  <p className="muted">
                    Answers come only from your documents, with citations. If your notes don't
                    cover it, you'll get "I don't know" instead of a guess.
                  </p>
                  <div className="suggestions">
                    {SUGGESTIONS.map((s) => (
                      <button key={s} className="suggestion" onClick={() => setInput(s)}>
                        {s}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble
              key={m.key}
              message={m}
              selected={m.key === selected?.key}
              activeCitation={activeCitation}
              onSelect={() => setSelectedKey(m.key)}
              onCitationClick={(n) => {
                setSelectedKey(m.key);
                setActiveCitation(n);
              }}
              onFeedback={(v) => m.id && void setFeedback(m.id, v)}
            />
          ))}
          <div ref={bottomRef} />
        </div>

        <form className="composer" onSubmit={submit}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask a question about your notes…  (Enter to send, Shift+Enter for a new line)"
            rows={2}
            maxLength={2000}
            aria-label="Your question"
          />
          {busy ? (
            <button type="button" className="secondary" onClick={stop}>
              Stop
            </button>
          ) : (
            <button type="submit" className="primary" disabled={!input.trim()}>
              Send
            </button>
          )}
        </form>
      </section>

      <SourcesPanel
        sources={selected?.sources ?? []}
        cited={selected?.cited ?? []}
        active={activeCitation}
        onSelect={setActiveCitation}
      />
    </div>
  );
}
