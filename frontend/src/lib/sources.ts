import type { AnswerMode, Citation } from "../api/types";

/** Uncited passages below this relevance are collapsed under "Other retrieved passages". */
export const LOW_RELEVANCE = 0.3;

/**
 * Split sources into what to show first and what to tuck away.
 * - While streaming we don't know what will be cited yet: show everything in order.
 * - Then: cited sources first (in order of first citation), then uncited but still relevant
 *   passages, and the rest (low relevance, or unused sections of a summary) collapsed.
 */
export function arrangeSources(
  sources: Citation[],
  cited: number[],
  mode: AnswerMode | undefined,
  streaming: boolean,
): { main: Citation[]; others: Citation[] } {
  if (streaming) return { main: sources, others: [] };
  const byN = new Map(sources.map((s) => [s.n, s]));
  const citedSources = cited.map((n) => byN.get(n)).filter((s): s is Citation => !!s);
  const uncited = sources
    .filter((s) => !cited.includes(s.n))
    .sort((a, b) => b.score - a.score);
  const keep = (s: Citation) => mode !== "summary" && s.score >= LOW_RELEVANCE;
  return {
    main: [...citedSources, ...uncited.filter(keep)],
    others: uncited.filter((s) => !keep(s)),
  };
}
