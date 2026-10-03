import { useEffect, useState } from "react";

import type { UiMessage } from "../hooks/useChat";
import { normalizeCitations } from "../lib/citations";
import AnswerMarkdown from "./AnswerMarkdown";

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
    <button
      className="ghost icon"
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
      {state === "copied" ? "Copied!" : state === "failed" ? "Copy failed" : "Copy"}
    </button>
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
      <div className="msg user">
        <div className="bubble">{m.content}</div>
      </div>
    );
  }

  const thinking = m.streaming && !m.content;
  const progress = m.status ?? (m.mode === "summary" ? "Reading your documents" : "Searching your documents");
  return (
    <div
      className={`msg assistant${selected ? " selected" : ""}`}
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
      <div className="bubble">
        {thinking ? (
          <span className="typing" aria-label={progress}>
            {progress.replace(/…$/, "")}
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
        ) : (
          <AnswerMarkdown
            text={m.content}
            sources={m.sources}
            activeCitation={selected ? activeCitation : null}
            onCitationClick={(n) => {
              onSelect();
              onCitationClick(n);
            }}
          />
        )}
        {m.streaming && m.content && <span className="cursor" aria-hidden />}
        {m.error && (
          <p className="error" role="alert">
            {m.error}
          </p>
        )}
        {m.stopped && <p className="hint">Stopped. This answer is incomplete and was not saved.</p>}
        {m.answered === false && !m.streaming && m.mode !== "summary" && (
          <p className="hint">
            Nothing in your documents answers this. Try rephrasing, or upload notes that cover it.
          </p>
        )}
      </div>
      {!m.streaming && (m.id || m.stopped) && !m.error && (
        <div className="msg-meta">
          {m.mode === "summary" && <span className="badge">summary</span>}
          {m.rewrittenQuestion && (
            <span className="small muted" title="Follow-up rewritten for retrieval">
              searched: “{m.rewrittenQuestion}”
            </span>
          )}
          {m.latency && <span className="small muted">{(m.latency.total_ms / 1000).toFixed(1)}s</span>}
          <span className="feedback">
            {m.content && <CopyButton text={m.content} />}
            {m.id && m.answered !== false && (
              <>
                <button
                  className={`ghost icon${m.feedback === 1 ? " on" : ""}`}
                  aria-label="Helpful"
                  onClick={(e) => {
                    e.stopPropagation();
                    onFeedback(1);
                  }}
                >
                  👍
                </button>
                <button
                  className={`ghost icon${m.feedback === -1 ? " on" : ""}`}
                  aria-label="Not helpful"
                  onClick={(e) => {
                    e.stopPropagation();
                    onFeedback(-1);
                  }}
                >
                  👎
                </button>
              </>
            )}
          </span>
        </div>
      )}
    </div>
  );
}
