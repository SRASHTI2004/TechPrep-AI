import type { UiMessage } from "../hooks/useChat";
import AnswerMarkdown from "./AnswerMarkdown";

interface Props {
  message: UiMessage;
  selected: boolean;
  activeCitation: number | null;
  onSelect: () => void;
  onCitationClick: (n: number) => void;
  onFeedback: (value: 1 | -1) => void;
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
  return (
    <div className={`msg assistant${selected ? " selected" : ""}`} onClick={onSelect}>
      <div className="bubble">
        {thinking ? (
          <span className="typing" aria-label="Searching your documents">
            Searching your documents<span>.</span>
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
        {m.answered === false && !m.streaming && (
          <p className="hint">
            Nothing in your documents answers this. Try rephrasing, or upload notes that cover it.
          </p>
        )}
      </div>
      {!m.streaming && m.id && !m.error && (
        <div className="msg-meta">
          {m.rewrittenQuestion && (
            <span className="small muted" title="Follow-up rewritten for retrieval">
              searched: “{m.rewrittenQuestion}”
            </span>
          )}
          {m.latency && <span className="small muted">{(m.latency.total_ms / 1000).toFixed(1)}s</span>}
          {m.answered !== false && (
            <span className="feedback">
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
            </span>
          )}
        </div>
      )}
    </div>
  );
}
