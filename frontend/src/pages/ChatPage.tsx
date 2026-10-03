import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { conversationsApi, documentsApi } from "../api/endpoints";
import type { Conversation } from "../api/types";
import MessageBubble from "../components/MessageBubble";
import SourcesPanel from "../components/SourcesPanel";
import VoiceInput from "../components/VoiceInput";
import { useChat } from "../hooks/useChat";

const SUGGESTIONS = [
  "What are the disadvantages of sharding?",
  "When should I use a CDN, and push vs pull?",
  "How does the 0-1 knapsack DP work?",
  "Give me a summary of my notes",
];

/** Set by the Documents page's "Summarize" button: navigate("/chat", { state }). */
export interface SummarizeRequest {
  summarize: { id: string; filename: string };
}

function ConversationItem({
  conversation: c,
  active,
  onRename,
  onDelete,
}: {
  conversation: Conversation;
  active: boolean;
  onRename: (title: string) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(c.title);

  if (editing) {
    const save = () => {
      const t = title.trim();
      if (t && t !== c.title) onRename(t);
      setEditing(false);
    };
    return (
      <li className={active ? "active" : ""}>
        <input
          className="rename-input"
          value={title}
          maxLength={200}
          autoFocus
          aria-label="Chat name"
          onChange={(e) => setTitle(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => {
            if (e.key === "Enter") save();
            if (e.key === "Escape") {
              setTitle(c.title);
              setEditing(false);
            }
          }}
        />
      </li>
    );
  }

  return (
    <li className={active ? "active" : ""}>
      <Link to={`/chat/${c.id}`} title={c.title}>
        {c.title}
      </Link>
      <button
        className="ghost icon"
        aria-label={`Rename conversation ${c.title}`}
        title="Rename"
        onClick={() => {
          setTitle(c.title);
          setEditing(true);
        }}
      >
        ✎
      </button>
      <button
        className="ghost icon danger"
        aria-label={`Delete conversation ${c.title}`}
        title="Delete"
        onClick={onDelete}
      >
        ×
      </button>
    </li>
  );
}

export default function ChatPage() {
  const { conversationId = null } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [scope, setScope] = useState<string[]>([]); // [] = all documents
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const handledSummarizeRef = useRef<string | null>(null);

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

  const invalidateConversations = () =>
    queryClient.invalidateQueries({ queryKey: ["conversations"] });
  const deleteConv = useMutation({
    mutationFn: conversationsApi.remove,
    onSuccess: (_, id) => {
      invalidateConversations();
      if (id === conversationId) navigate("/chat");
    },
  });
  const renameConv = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => conversationsApi.rename(id, title),
    onSettled: invalidateConversations,
  });

  // The sources panel follows the selected assistant message (default: the latest one).
  const assistantMessages = messages.filter((m) => m.role === "assistant");
  const selected = useMemo(
    () =>
      assistantMessages.find((m) => m.key === selectedKey) ??
      assistantMessages[assistantMessages.length - 1],
    [assistantMessages, selectedKey],
  );
  // The question each answer belongs to (the user message right before it).
  const selectedQuestion = useMemo(() => {
    const i = messages.findIndex((m) => m.key === selected?.key);
    return i > 0 && messages[i - 1]!.role === "user" ? messages[i - 1]!.content : undefined;
  }, [messages, selected]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  useEffect(() => {
    setSelectedKey(null);
    setActiveCitation(null);
  }, [conversationId]);

  const ask = useCallback(
    (text: string, documentIds: string[] | null, mode: "auto" | "summary" = "auto") => {
      setSelectedKey(null);
      setActiveCitation(null);
      void send(text, documentIds, { mode });
    },
    [send],
  );

  // "Summarize" on the Documents page opens a new chat and asks for the summary right away.
  useEffect(() => {
    const request = (location.state as SummarizeRequest | null)?.summarize;
    if (!request || handledSummarizeRef.current === location.key) return;
    handledSummarizeRef.current = location.key;
    navigate(location.pathname, { replace: true, state: null });
    ask(`Summarize ${request.filename}`, [request.id], "summary");
  }, [location, navigate, ask]);

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    ask(text, scope.length ? scope : null);
  }

  function summarizeScope() {
    if (busy) return;
    const names = readyDocs.filter((d) => scope.includes(d.id)).map((d) => d.filename);
    const what = names.length ? names.join(", ") : "all my documents";
    ask(`Summarize ${what}`, scope.length ? scope : null, "summary");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) submit();
  }

  const appendVoiceText = useCallback(
    (text: string) => setInput((current) => (current.trim() ? `${current.trimEnd()} ${text}` : text)),
    [],
  );

  const noDocs = documents.isSuccess && readyDocs.length === 0;

  return (
    <div className="chat-layout">
      <aside className="conversations">
        <button className="primary block" onClick={() => navigate("/chat")}>
          + New chat
        </button>
        <ul>
          {(conversations.data ?? []).map((c) => (
            <ConversationItem
              key={c.id}
              conversation={c}
              active={c.id === conversationId}
              onRename={(title) => renameConv.mutate({ id: c.id, title })}
              onDelete={() => {
                if (window.confirm(`Delete the chat "${c.title}"? This cannot be undone.`)) {
                  deleteConv.mutate(c.id);
                }
              }}
            />
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
                <div key={d.id} className="scope-row">
                  <label>
                    <input
                      type="checkbox"
                      checked={scope.includes(d.id)}
                      onChange={(e) =>
                        setScope((s) => (e.target.checked ? [...s, d.id] : s.filter((x) => x !== d.id)))
                      }
                    />
                    {d.filename}
                  </label>
                  <button
                    type="button"
                    className="ghost small"
                    disabled={busy}
                    aria-label={`Summarize ${d.filename}`}
                    onClick={() => ask(`Summarize ${d.filename}`, [d.id], "summary")}
                  >
                    Summarize
                  </button>
                </div>
              ))}
              {scope.length > 0 && (
                <button className="ghost" onClick={() => setScope([])}>
                  Clear (search all)
                </button>
              )}
            </div>
          </details>
          <button
            type="button"
            className="secondary summarize-btn"
            onClick={summarizeScope}
            disabled={busy || noDocs}
            title="Summarize the selected documents (or all documents if none are selected)"
          >
            Summarize {scope.length ? "selected" : "all"}
          </button>
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
                  <p className="muted small">
                    Want an overview? Ask “summarize this document”, or use{" "}
                    <strong>Summarize</strong> above (pick documents under “Search in” to summarize
                    just those).
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
              onSelect={() => {
                if (m.key !== selected?.key) setActiveCitation(null);
                setSelectedKey(m.key);
              }}
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
          <VoiceInput onText={appendVoiceText} disabled={busy} />
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
              Stop generating
            </button>
          ) : (
            <button type="submit" className="primary" disabled={!input.trim()}>
              Send
            </button>
          )}
        </form>
      </section>

      <SourcesPanel
        key={selected?.key ?? "none"}
        sources={selected?.sources ?? []}
        cited={selected?.cited ?? []}
        active={activeCitation}
        onSelect={setActiveCitation}
        mode={selected?.mode}
        streaming={selected?.streaming}
        label={selectedQuestion}
      />
    </div>
  );
}
