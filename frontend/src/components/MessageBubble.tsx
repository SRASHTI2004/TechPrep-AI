import { AlertCircle, Check, Clock, Copy, Info, Search, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";

import type { UiMessage } from "../hooks/useChat";
import { normalizeCitations } from "../lib/citations";
import { cn } from "../lib/utils";
import AnswerMarkdown from "./AnswerMarkdown";
import { LogoMark } from "./Logo";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

interface Props {
  message: UiMessage;
  selected: boolean;
  activeCitation: number | null;
  onSelect: () => void;
  onCitationClick: (n: number) => void;
  onFeedback: (value: 1 | -1) => void;
}

function CopyButton({ text }: { text: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    if (state === "idle") return;
    const t = setTimeout(() => setState("idle"), 1500);
    return () => clearTimeout(t);
  }, [state]);

  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-7 gap-1.5 px-2"
      aria-label="Copy answer"
      title="Copy answer"
      onClick={async (e) => {
        e.stopPropagation();
        try {
          await navigator.clipboard.writeText(normalizeCitations(text));
          setState("copied");
        } catch {
          setState("failed");
        }
      }}
    >
      {state === "copied" ? <Check className="text-success" /> : <Copy />}
      <span className={cn(state === "idle" && "sr-only")}>
        {state === "copied" ? "Copied!" : state === "failed" ? "Copy failed" : "Copy"}
      </span>
    </Button>
  );
}

function Thinking({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2.5 text-sm text-muted-foreground" aria-label={label}>
      <Search className="size-4 animate-pulse text-primary" />
      <span>{label.replace(/…$/, "")}</span>
      <span className="flex gap-1" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 animate-blink rounded-full bg-primary"
            style={{ animationDelay: `${i * 0.18}s` }}
          />
        ))}
      </span>
    </div>
  );
}

export default function MessageBubble({
  message: m,
  selected,
  activeCitation,
  onSelect,
  onCitationClick,
  onFeedback,
}: Props) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-[0.925rem] leading-relaxed text-primary-foreground shadow-sm sm:max-w-[75%]">
          {m.content}
        </div>
      </div>
    );
  }

  const thinking = m.streaming && !m.content;
  const progress = m.status ?? (m.mode === "summary" ? "Reading your documents" : "Searching your documents");
  return (
    <div className="group/msg flex gap-3">
      <LogoMark className="mt-1 hidden size-7 rounded-md sm:grid" />
      <div className="min-w-0 flex-1">
        <div
          className={cn(
            "cursor-pointer rounded-2xl rounded-tl-md border bg-card px-4 py-3 shadow-sm transition-[border-color,box-shadow] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            selected
              ? "border-primary/40 shadow-[inset_3px_0_0_hsl(var(--primary))]"
              : "hover:border-primary/25",
          )}
          onClick={onSelect}
          tabIndex={0}
          aria-label={selected ? "Answer (its sources are shown)" : "Answer: show its sources"}
          onKeyDown={(e) => {
            if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
              e.preventDefault();
              onSelect();
            }
          }}
        >
          {thinking ? (
            <Thinking label={progress} />
          ) : (
            <AnswerMarkdown
              text={m.content}
              sources={m.sources}
              // No id = never finalized (still streaming, stopped or cut off): tidy partial Markdown.
              streaming={m.streaming || !m.id}
              activeCitation={selected ? activeCitation : null}
              onCitationClick={(n) => {
                onSelect();
                onCitationClick(n);
              }}
            />
          )}
          {m.streaming && m.content && (
            <span className="ml-0.5 inline-block h-4 w-[3px] animate-blink rounded-sm bg-primary align-[-0.2em]" aria-hidden />
          )}
          {m.error && (
            <div
              className="mt-2 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              role="alert"
            >
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              {m.error}
            </div>
          )}
          {m.stopped && (
            <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Info className="size-3.5" /> Stopped. This answer is incomplete and was not saved.
            </p>
          )}
          {m.answered === false && !m.streaming && m.mode !== "summary" && (
            <p className="mt-3 flex items-start gap-2 rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
              <Info className="mt-px size-3.5 shrink-0" />
              Nothing in your documents answers this. Try rephrasing, or upload notes that cover it.
            </p>
          )}
        </div>

        {!m.streaming && (m.id || m.stopped) && !m.error && (
          <div className="mt-1 flex min-h-8 flex-wrap items-center gap-x-3 gap-y-1 px-1 text-xs text-muted-foreground">
            {m.mode === "summary" && (
              <Badge variant="default" className="capitalize">
                <Sparkles />
                summary
              </Badge>
            )}
            {m.rewrittenQuestion && (
              <span className="max-w-full truncate" title="Follow-up rewritten for retrieval">
                searched: “{m.rewrittenQuestion}”
              </span>
            )}
            {m.latency && (
              <span className="inline-flex items-center gap-1">
                <Clock className="size-3" />
                <span>{(m.latency.total_ms / 1000).toFixed(1)}s</span>
              </span>
            )}
            <span className="ml-auto flex items-center gap-0.5 opacity-100 transition-opacity sm:opacity-70 sm:group-hover/msg:opacity-100">
              {m.content && <CopyButton text={m.content} />}
              {m.id && m.answered !== false && (
                <>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className={cn("size-7", m.feedback === 1 && "bg-accent text-accent-foreground")}
                    aria-label="Helpful"
                    aria-pressed={m.feedback === 1}
                    onClick={(e) => {
                      e.stopPropagation();
                      onFeedback(1);
                    }}
                  >
                    <ThumbsUp />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className={cn("size-7", m.feedback === -1 && "bg-accent text-accent-foreground")}
                    aria-label="Not helpful"
                    aria-pressed={m.feedback === -1}
                    onClick={(e) => {
                      e.stopPropagation();
                      onFeedback(-1);
                    }}
                  >
                    <ThumbsDown />
                  </Button>
                </>
              )}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
