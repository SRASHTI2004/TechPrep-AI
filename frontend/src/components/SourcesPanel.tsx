import { useEffect, useRef } from "react";

import type { Citation } from "../api/types";
import { formatLocation } from "../lib/citations";

interface Props {
  sources: Citation[];
  cited: number[];
  active: number | null;
  onSelect: (n: number) => void;
}

export default function SourcesPanel({ sources, cited, active, onSelect }: Props) {
  const refs = useRef(new Map<number, HTMLLIElement>());

  useEffect(() => {
    if (active !== null) refs.current.get(active)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [active]);

  if (!sources.length) {
    return (
      <aside className="sources">
        <h3>Sources</h3>
        <p className="muted small">
          Sources used for an answer appear here. Click a citation number to jump to its source.
        </p>
      </aside>
    );
  }

  return (
    <aside className="sources">
      <h3>Sources</h3>
      <ol>
        {sources.map((s) => (
          <li
            key={s.chunk_id}
            ref={(el) => {
              if (el) refs.current.set(s.n, el);
            }}
            className={`source-card${active === s.n ? " active" : ""}${
              cited.includes(s.n) ? "" : " uncited"
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
            <p className="snippet">{s.snippet}…</p>
            <div className="small muted">
              relevance {(s.score * 100).toFixed(0)}%{cited.includes(s.n) ? " · cited" : " · not cited"}
            </div>
          </li>
        ))}
      </ol>
    </aside>
  );
}
