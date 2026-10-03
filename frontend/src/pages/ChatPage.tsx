import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUp,
  BookOpen,
  ChevronDown,
  Code2,
  Database,
  FileStack,
  Globe,
  Library,
  PanelLeft,
  RotateCcw,
  Sparkles,
  Square,
  UploadCloud,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { conversationsApi, documentsApi } from "../api/endpoints";
import type { Conversation } from "../api/types";
import ConversationList from "../components/ConversationList";
import { LogoMark } from "../components/Logo";
import MessageBubble from "../components/MessageBubble";
import SourcesPanel from "../components/SourcesPanel";
import { Button } from "../components/ui/button";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { EmptyState } from "../components/ui/empty-state";
import { Popover, PopoverContent, PopoverTrigger } from "../components/ui/popover";
import { Sheet, SheetContent } from "../components/ui/sheet";
import { Skeleton } from "../components/ui/skeleton";
import VoiceInput from "../components/VoiceInput";
import { useChat } from "../hooks/useChat";
import { cn } from "../lib/utils";

const SUGGESTIONS = [
  { icon: Database, text: "What are the disadvantages of sharding?" },
  { icon: Globe, text: "When should I use a CDN, and push vs pull?" },
  { icon: Code2, text: "How does the 0-1 knapsack DP work?" },
  { icon: FileStack, text: "Give me a summary of my notes" },
];

/** Set by the Documents page's "Summarize" button: navigate("/chat", { state }). */
export interface SummarizeRequest {
  summarize: { id: string; filename: string };
}

/** The sources panel is a side column on wide screens and a sheet below that. */
const isWide = () =>
  typeof window.matchMedia !== "function" || window.matchMedia("(min-width: 1280px)").matches;

function HistorySkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-label="Loading conversation">
      {[0, 1].map((i) => (
        <div key={i} className="flex flex-col gap-6">
          <div className="flex justify-end">
            <Skeleton className="h-10 w-2/5 rounded-2xl rounded-br-md" />
          </div>
          <div className="flex gap-3">
            <Skeleton className="size-7 rounded-md" />
            <div className="flex-1 space-y-2.5 rounded-2xl border bg-card p-4">
              <Skeleton className="h-3 w-11/12" />
              <Skeleton className="h-3 w-4/5" />
              <Skeleton className="h-3 w-3/5" />
            </div>
          </div>
        </div>
      ))}
    </div>
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
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [toDelete, setToDelete] = useState<Conversation | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const handledSummarizeRef = useRef<string | null>(null);

  const onCreated = useCallback(
    (id: string) => navigate(`/chat/${id}`, { replace: true }),
    [navigate],
  );
  const { messages, loadingHistory, historyError, reloadHistory, busy, send, stop, setFeedback } =
    useChat(conversationId, onCreated);

  const conversations = useQuery({ queryKey: ["conversations"], queryFn: conversationsApi.list });
  const documents = useQuery({ queryKey: ["documents"], queryFn: documentsApi.list });
  const readyDocs = (documents.data?.items ?? []).filter((d) => d.status === "ready");

  const invalidateConversations = () =>
    queryClient.invalidateQueries({ queryKey: ["conversations"] });
  const deleteConv = useMutation({
    mutationFn: conversationsApi.remove,
    onSuccess: (_, id) => {
      invalidateConversations();
      toast.success("Chat deleted");
      if (id === conversationId) navigate("/chat");
    },
    onError: (err) => toast.error("Could not delete the chat", { description: err.message }),
  });
  const renameConv = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => conversationsApi.rename(id, title),
    onSuccess: () => toast.success("Chat renamed"),
    onError: (err) => toast.error("Could not rename the chat", { description: err.message }),
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

  // Grow the question box with its content (up to a limit).
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  }, [input]);

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
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const appendVoiceText = useCallback(
    (text: string) => setInput((current) => (current.trim() ? `${current.trimEnd()} ${text}` : text)),
    [],
  );

  const noDocs = documents.isSuccess && readyDocs.length === 0;
  const title = conversations.data?.find((c) => c.id === conversationId)?.title ?? "New chat";
  const sourceCount = selected?.sources.length ?? 0;

  const conversationList = (onNavigate?: () => void) => (
    <ConversationList
      conversations={conversations.data}
      isLoading={conversations.isLoading}
      error={conversations.error}
      onRetry={() => void conversations.refetch()}
      activeId={conversationId}
      onNew={() => {
        navigate("/chat");
        onNavigate?.();
      }}
      onRename={(id, t) => renameConv.mutate({ id, title: t })}
      onDelete={setToDelete}
      onNavigate={onNavigate}
    />
  );

  const sourcesPanel = (props: { className?: string; hideTitle?: boolean }) => (
    <SourcesPanel
      key={selected?.key ?? "none"}
      sources={selected?.sources ?? []}
      cited={selected?.cited ?? []}
      active={activeCitation}
      onSelect={setActiveCitation}
      mode={selected?.mode}
      streaming={selected?.streaming}
      label={selectedQuestion}
      {...props}
    />
  );

  return (
    <div className="flex h-full">
      <aside className="hidden w-72 shrink-0 border-r bg-card/40 lg:block">{conversationList()}</aside>

      <section className="flex min-w-0 flex-1 flex-col">
        {/* Chat header */}
        <div className="flex h-14 shrink-0 items-center gap-2 border-b bg-card/40 px-3 sm:px-4">
          <Button
            variant="ghost"
            size="icon-sm"
            className="lg:hidden"
            aria-label="Show chats"
            onClick={() => setHistoryOpen(true)}
          >
            <PanelLeft />
          </Button>
          <h1 className="min-w-0 truncate text-sm font-semibold" title={title}>
            {title}
          </h1>

          <div className="ml-auto flex items-center gap-1.5">
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" size="sm" className="max-w-[11rem]" aria-label="Choose documents to search">
                  <Library />
                  <span className="hidden truncate sm:inline">
                    {scope.length ? `${scope.length} selected` : "All documents"}
                  </span>
                  {scope.length > 0 && (
                    <span className="rounded bg-accent px-1 text-[0.7rem] text-accent-foreground sm:hidden">
                      {scope.length}
                    </span>
                  )}
                  <ChevronDown className="!size-3.5 text-muted-foreground" />
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80">
                <div className="px-2 pb-1.5 pt-1">
                  <div className="text-sm font-semibold">Search in</div>
                  <div className="text-xs text-muted-foreground">
                    {scope.length ? "Only the selected documents" : "All your ready documents"}
                  </div>
                </div>
                <div className="max-h-72 overflow-y-auto">
                  {readyDocs.length === 0 && (
                    <p className="px-2 py-4 text-center text-xs text-muted-foreground">
                      No ready documents.{" "}
                      <Link to="/documents" className="font-medium text-primary hover:underline">
                        Upload some
                      </Link>
                    </p>
                  )}
                  {readyDocs.map((d) => (
                    <div key={d.id} className="group/doc flex items-center gap-1 rounded-md hover:bg-muted">
                      <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2.5 px-2 py-1.5 text-sm">
                        <input
                          type="checkbox"
                          className="size-4 shrink-0 cursor-pointer rounded accent-[hsl(var(--primary))]"
                          checked={scope.includes(d.id)}
                          onChange={(e) =>
                            setScope((s) => (e.target.checked ? [...s, d.id] : s.filter((x) => x !== d.id)))
                          }
                        />
                        <span className="truncate" title={d.filename}>
                          {d.filename}
                        </span>
                      </label>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="mr-1 size-7"
                        disabled={busy}
                        aria-label={`Summarize ${d.filename}`}
                        title={`Summarize ${d.filename}`}
                        onClick={() => ask(`Summarize ${d.filename}`, [d.id], "summary")}
                      >
                        <Sparkles className="!size-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
                {scope.length > 0 && (
                  <div className="mt-1 border-t pt-1">
                    <Button variant="ghost" size="sm" className="w-full justify-start" onClick={() => setScope([])}>
                      Clear (search all)
                    </Button>
                  </div>
                )}
              </PopoverContent>
            </Popover>

            <Button
              variant="outline"
              size="sm"
              onClick={summarizeScope}
              disabled={busy || noDocs}
              title="Summarize the selected documents (or all documents if none are selected)"
            >
              <Sparkles className="text-primary" />
              <span className="sr-only sm:not-sr-only">Summarize {scope.length ? "selected" : "all"}</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              className="xl:hidden"
              aria-label={`Show sources (${sourceCount})`}
              onClick={() => setSourcesOpen(true)}
            >
              <BookOpen />
              <span className="tabular-nums">{sourceCount}</span>
            </Button>
          </div>
        </div>

        {/* Messages */}
        <div className="min-h-0 flex-1 overflow-y-auto" aria-live="polite">
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
            {loadingHistory && <HistorySkeleton />}
            {!loadingHistory && historyError && (
              <EmptyState
                tone="error"
                icon={AlertTriangle}
                title="Could not load this conversation"
                description={historyError}
                action={
                  <Button variant="outline" onClick={reloadHistory}>
                    <RotateCcw /> Try again
                  </Button>
                }
              />
            )}
            {!loadingHistory && !historyError && messages.length === 0 && (
              noDocs ? (
                <EmptyState
                  className="py-16"
                  icon={UploadCloud}
                  title="Add your notes to get started"
                  description="You have no documents yet. Upload notes or PDFs and TechPrep AI will answer questions from them, with citations."
                  action={
                    <Button asChild>
                      <Link to="/documents">
                        <UploadCloud /> Upload notes or PDFs
                      </Link>
                    </Button>
                  }
                />
              ) : (
                <div className="flex flex-col items-center py-8 text-center sm:py-12">
                  <LogoMark className="size-12 rounded-xl" />
                  <h2 className="mt-5 text-2xl font-semibold tracking-tight">Ask your notes anything</h2>
                  <p className="mt-2 max-w-md text-sm text-muted-foreground">
                    Answers come only from your documents, with citations. If your notes don't
                    cover it, you'll get "I don't know" instead of a guess.
                  </p>
                  <div className="mt-8 grid w-full gap-2.5 sm:grid-cols-2">
                    {SUGGESTIONS.map(({ icon: Icon, text }) => (
                      <button
                        key={text}
                        type="button"
                        className="group flex items-start gap-3 rounded-xl border bg-card p-3.5 text-left text-sm shadow-sm transition-all hover:-translate-y-px hover:border-primary/40 hover:shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={() => {
                          setInput(text);
                          textareaRef.current?.focus();
                        }}
                      >
                        <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
                        {text}
                      </button>
                    ))}
                  </div>
                  <p className="mt-6 max-w-md text-xs text-muted-foreground">
                    Want an overview? Ask “summarize this document”, or use{" "}
                    <strong className="font-medium text-foreground">Summarize</strong> above (pick
                    documents under “All documents” to summarize just those).
                  </p>
                </div>
              )
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
                  if (!isWide()) setSourcesOpen(true);
                }}
                onFeedback={(v) =>
                  m.id &&
                  setFeedback(m.id, v).then(
                    () => toast.success("Thanks for the feedback"),
                    (err: Error) => toast.error("Could not save feedback", { description: err.message }),
                  )
                }
              />
            ))}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Composer */}
        <div className="shrink-0 px-3 pb-3 sm:px-6 sm:pb-5">
          <form
            onSubmit={submit}
            className="mx-auto w-full max-w-3xl rounded-2xl border bg-card shadow-soft transition-shadow focus-within:border-primary/50 focus-within:ring-4 focus-within:ring-ring/10"
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask a question about your notes…"
              rows={1}
              maxLength={2000}
              aria-label="Your question"
              className="block max-h-[200px] min-h-[52px] w-full resize-none bg-transparent px-4 pb-1 pt-3.5 text-[0.95rem] placeholder:text-muted-foreground focus:outline-none"
            />
            <div className="flex items-center gap-2 px-2.5 pb-2.5">
              <VoiceInput onText={appendVoiceText} disabled={busy} />
              <span className="ml-auto hidden text-xs text-muted-foreground md:inline">
                <kbd className="rounded border bg-muted px-1 font-sans">Enter</kbd> to send ·{" "}
                <kbd className="rounded border bg-muted px-1 font-sans">Shift+Enter</kbd> new line
              </span>
              {busy ? (
                <Button type="button" variant="secondary" size="sm" className="ml-auto md:ml-0" onClick={stop}>
                  <Square className="!size-3 fill-current" /> Stop generating
                </Button>
              ) : (
                <Button
                  type="submit"
                  size="icon-sm"
                  className={cn("ml-auto rounded-lg md:ml-0", !input.trim() && "bg-muted-foreground/30")}
                  disabled={!input.trim()}
                  aria-label="Send"
                >
                  <ArrowUp />
                </Button>
              )}
            </div>
          </form>
          <p className="mt-2 text-center text-[0.7rem] text-muted-foreground">
            Answers are generated only from your documents. Check the cited sources.
          </p>
        </div>
      </section>

      {sourcesPanel({ className: "hidden w-[22rem] shrink-0 overflow-y-auto border-l bg-card/40 xl:flex" })}

      <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
        <SheetContent side="left" title="Chats" className="max-w-xs">
          {conversationList(() => setHistoryOpen(false))}
        </SheetContent>
      </Sheet>
      <Sheet open={sourcesOpen} onOpenChange={setSourcesOpen}>
        <SheetContent side="right" title="Sources">
          {sourcesPanel({ hideTitle: true })}
        </SheetContent>
      </Sheet>

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(open) => !open && setToDelete(null)}
        title="Delete this chat?"
        description={`"${toDelete?.title ?? ""}" and all its messages will be deleted. This cannot be undone.`}
        onConfirm={() => toDelete && deleteConv.mutate(toDelete.id)}
      />
    </div>
  );
}
