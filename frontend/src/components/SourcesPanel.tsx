import { useEffect, useRef, useState } from "react";

import type { AnswerMode, Citation } from "../api/types";
import { formatLocation } from "../lib/citations";
import { arrangeSources } from "../lib/sources";

interface Props {
  sources: Citation[];
  cited: number[];
  active: number | null;
  onSelect: (n: number) => void;
  mode?: AnswerMode;
  streaming?: boolean;
  /** Which answer the panel belongs to, e.g. the question that was asked. */
  label?: string;
}

export default function SourcesPanel({
  sources,
  cited,
  active,
  onSelect,
  mode,
  streaming = false,
  label,
}: Props) {
  const refs = useRef(new Map<number, HTMLLIElement>());
  const [showOthers, setShowOthers] = useState(false);
  const { main, others } = arrangeSources(sources, cited, mode, streaming);

  // Clicking a citation chip whose source is collapsed opens the collapsed group.
  const activeIsHidden = active !== null && others.some((s) => s.n === active);
  useEffect(() => {
    if (activeIsHidden) setShowOthers(true);
  }, [active, activeIsHidden]);

  useEffect(() => {
    if (active !== null) refs.current.get(active)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [active, showOthers]);

  if (!sources.length) {
    return (
      <aside className="sources">
        <h3>Sources</h3>
        <p className="muted small">
          Sources used for an answer appear here. Click an answer to see its sources, or a
          citation number to jump to one.
        </p>
      </aside>
    );
  }

  const card = (s: Citation) => {
    const isCited = cited.includes(s.n);
    return (
      <li
        key={s.chunk_id}
        ref={(el) => {
          if (el) refs.current.set(s.n, el);
        }}
        className={`source-card${active === s.n ? " active" : ""}${
          isCited || streaming ? "" : " uncited"
        }`}
        onClick={() => onSelect(s.n)}
      >
        <div className="source-head">
          <span className="cite-chip static">{s.n}</span>
          <span className="source-file" title={s.filename}>
            {s.filename}
          </span>
          <span className="source-loc">{formatLocation(s.page, s.section)}</span>
        </div>
        {s.section && !s.page && <div className="source-section small muted">{s.section}</div>}
        {s.section && s.page && s.section.startsWith("pp.") && (
          <div className="source-section small muted">{s.section}</div>
        )}
        <p className="snippet">{s.snippet}…</p>
        {!streaming && (
          <div className="small muted">
            {mode === "summary" ? "document section" : `relevance ${(s.score * 100).toFixed(0)}%`}
            {isCited ? " · cited" : " · not cited"}
          </div>
        )}
      </li>
    );
  };

  return (
    <aside className="sources">
      <h3>Sources</h3>
      {label && (
        <p className="sources-for small muted" title={label}>
          For: “{label}”
        </p>
      )}
      <ol>{main.map(card)}</ol>
      {others.length > 0 && (
        <div className="other-sources">
          <button
            type="button"
            className="ghost block other-toggle"
            aria-expanded={showOthers}
            onClick={() => setShowOthers((v) => !v)}
          >
            {showOthers ? "▾" : "▸"} Other retrieved passages ({others.length})
          </button>
          {showOthers && <ol>{others.map(card)}</ol>}
        </div>
      )}
    </aside>
  );
}
