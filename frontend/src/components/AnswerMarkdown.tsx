import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Citation } from "../api/types";
import { citationNumberFromHref, linkifyCitations } from "../lib/citations";

interface Props {
  text: string;
  sources: Citation[];
  activeCitation?: number | null;
  onCitationClick?: (n: number) => void;
}

/** Renders an answer as Markdown, with [n] markers as chips that select the source. */
export default function AnswerMarkdown({ text, sources, activeCitation, onCitationClick }: Props) {
  const valid = useMemo(() => new Set(sources.map((s) => s.n)), [sources]);
  const linked = useMemo(() => linkifyCitations(text, valid), [text, valid]);

  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children }) {
            const n = citationNumberFromHref(href);
            if (n === null) {
              return (
                <a href={href} target="_blank" rel="noreferrer noopener">
                  {children}
                </a>
              );
            }
            const source = sources.find((s) => s.n === n);
            const label = source
              ? `${source.filename}${source.page ? `, p. ${source.page}` : ""}`
              : `Source ${n}`;
            return (
              <button
                type="button"
                className={`cite-chip${activeCitation === n ? " active" : ""}`}
                title={label}
                aria-label={`Show source ${n}: ${label}`}
                onClick={() => onCitationClick?.(n)}
              >
                {n}
              </button>
            );
          },
        }}
      >
        {linked}
      </ReactMarkdown>
    </div>
  );
}
