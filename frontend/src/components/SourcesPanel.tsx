import { BookOpen, ChevronRight, FileText } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { AnswerMode, Citation } from "../api/types";
import { formatLocation } from "../lib/citations";
import { arrangeSources } from "../lib/sources";
import { cn } from "../lib/utils";
import { citeChipClass } from "./AnswerMarkdown";
import { Skeleton } from "./ui/skeleton";

interface Props {
  sources: Citation[];
  cited: number[];
  active: number | null;
  onSelect: (n: number) => void;
  mode?: AnswerMode;
  streaming?: boolean;
  /** Which answer the panel belongs to, e.g. the question that was asked. */
  label?: string;
  className?: string;
  /** Shown inside a sheet that already has its own title. */
  hideTitle?: boolean;
}

export default function SourcesPanel({
  sources,
  cited,
  active,
  onSelect,
  mode,
  streaming = false,
  label,
  className,
  hideTitle = false,
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

  const title = !hideTitle && (
    <div className="flex items-center gap-2">
      <BookOpen className="size-4 text-primary" />
      <h2 className="text-sm font-semibold">Sources</h2>
      {sources.length > 0 && (
        <span className="rounded-full bg-muted px-1.5 text-xs font-medium tabular-nums text-muted-foreground">
          {sources.length}
        </span>
      )}
    </div>
  );

  if (!sources.length) {
    return (
      <aside className={cn("sources flex flex-col gap-4 p-4", className)}>
        {title}
        {streaming ? (
          <div className="flex flex-col gap-3" aria-label="Finding sources">
            {[0, 1, 2].map((i) => (
              <div key={i} className="space-y-2.5 rounded-xl border bg-card p-3.5">
                <div className="flex items-center gap-2">
                  <Skeleton className="size-5 rounded-md" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
                <Skeleton className="h-2.5 w-full" />
                <Skeleton className="h-2.5 w-4/5" />
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center rounded-xl border border-dashed px-5 py-10 text-center">
            <span className="mb-3 grid size-10 place-items-center rounded-xl bg-accent text-accent-foreground">
              <BookOpen className="size-4" />
            </span>
            <p className="text-sm font-medium">No sources yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Sources used for an answer appear here. Click an answer to see its sources, or a
              citation number to jump to one.
            </p>
          </div>
        )}
      </aside>
    );
  }

  const card = (s: Citation) => {
    const isCited = cited.includes(s.n);
    const isActive = active === s.n;
    const relevance = Math.round(s.score * 100);
    return (
      <li
        key={s.chunk_id}
        ref={(el) => {
          if (el) refs.current.set(s.n, el);
        }}
        className={cn(
          "source-card cursor-pointer rounded-xl border bg-card p-3.5 shadow-sm transition-all hover:border-primary/40 hover:shadow-soft",
          isActive && "active border-primary bg-accent/60 ring-2 ring-primary/20",
          !isCited && !streaming && !isActive && "opacity-75",
        )}
        onClick={() => onSelect(s.n)}
      >
        <div className="flex items-center gap-2 text-sm">
          <span
            className={cn(
              citeChipClass,
              "mx-0 shrink-0",
              isActive ? "bg-primary text-primary-foreground ring-primary" : "bg-accent text-accent-foreground ring-primary/20",
            )}
          >
            {s.n}
          </span>
          <FileText className="size-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate font-medium" title={s.filename}>
            {s.filename}
          </span>
          {s.page && (
            <span className="ml-auto shrink-0 whitespace-nowrap text-xs text-muted-foreground">
              {formatLocation(s.page, s.section)}
            </span>
          )}
        </div>
        {s.section && !s.page && (
          <div className="mt-1 truncate text-xs text-muted-foreground" title={s.section}>
            {s.section.split(" > ").join(" › ")}
          </div>
        )}
        {s.section && s.page && s.section.startsWith("pp.") && (
          <div className="mt-1 text-xs text-muted-foreground">{s.section}</div>
        )}
        <p
          className={cn(
            "my-2 whitespace-pre-wrap border-l-2 pl-2.5 text-[0.8rem] leading-relaxed text-foreground/80 [overflow-wrap:anywhere]",
            isActive ? "border-primary" : "line-clamp-4 border-border",
          )}
        >
          {s.snippet}…
        </p>
        {!streaming && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {mode !== "summary" && (
              <span className="h-1 w-10 overflow-hidden rounded-full bg-muted" aria-hidden>
                <span
                  className={cn("block h-full rounded-full", isCited ? "bg-primary" : "bg-muted-foreground/40")}
                  style={{ width: `${Math.max(4, Math.min(100, relevance))}%` }}
                />
              </span>
            )}
            <span>
              {mode === "summary" ? "document section" : `relevance ${relevance}%`}
              {isCited ? " · cited" : " · not cited"}
            </span>
          </div>
        )}
      </li>
    );
  };

  return (
    <aside className={cn("sources flex flex-col gap-3 p-4", className)}>
      {title}
      {label && (
        <p className="-mt-1 truncate text-xs text-muted-foreground" title={label}>
          For: “{label}”
        </p>
      )}
      <ol className="flex flex-col gap-2.5">{main.map(card)}</ol>
      {others.length > 0 && (
        <div className="flex flex-col gap-2.5">
          <button
            type="button"
            className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-left text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-expanded={showOthers}
            onClick={() => setShowOthers((v) => !v)}
          >
            <ChevronRight className={cn("size-3.5 transition-transform", showOthers && "rotate-90")} />
            Other retrieved passages ({others.length})
          </button>
          {showOthers && <ol className="flex flex-col gap-2.5">{others.map(card)}</ol>}
        </div>
      )}
    </aside>
  );
}
