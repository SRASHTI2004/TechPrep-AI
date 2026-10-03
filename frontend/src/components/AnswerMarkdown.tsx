import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Citation } from "../api/types";
import { citationNumberFromHref, linkifyCitations } from "../lib/citations";
import { completeStreamingMarkdown } from "../lib/markdown";
import { cn } from "../lib/utils";

interface Props {
  text: string;
  sources: Citation[];
  activeCitation?: number | null;
  onCitationClick?: (n: number) => void;
  /** The text is still arriving: hide half-written Markdown syntax. */
  streaming?: boolean;
}

export const citeChipClass =
  "mx-0.5 inline-flex h-[1.3rem] min-w-[1.3rem] items-center justify-center rounded-md px-1 align-[0.12em] text-[0.7rem] font-semibold leading-none no-underline ring-1 ring-inset transition-colors";

/** Renders an answer as Markdown, with [n] markers as chips that select the source. */
export default function AnswerMarkdown({ text, sources, activeCitation, onCitationClick, streaming }: Props) {
  const valid = useMemo(() => new Set(sources.map((s) => s.n)), [sources]);
  const linked = useMemo(
    () => linkifyCitations(streaming ? completeStreamingMarkdown(text) : text, valid),
    [text, valid, streaming],
  );

  return (
    <div className="answer-prose">
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
            const active = activeCitation === n;
            return (
              <button
                type="button"
                className={cn(
                  citeChipClass,
                  "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "bg-primary text-primary-foreground ring-primary"
                    : "bg-accent text-accent-foreground ring-primary/20 hover:bg-primary hover:text-primary-foreground",
                )}
                title={label}
                aria-label={`Show source ${n}: ${label}`}
                aria-pressed={active}
                onClick={(e) => {
                  e.stopPropagation(); // the answer bubble's own click would reset the selection
                  onCitationClick?.(n);
                }}
              >
                {n}
              </button>
            );
          },
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto">
                <table className="!my-0">{children}</table>
              </div>
            );
          },
        }}
      >
        {linked}
      </ReactMarkdown>
    </div>
  );
}
