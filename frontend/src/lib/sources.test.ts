import type { Citation } from "../api/types";
import { arrangeSources } from "./sources";

const src = (n: number, score: number): Citation => ({
  n,
  chunk_id: `c${n}`,
  document_id: "d1",
  filename: "notes.md",
  page: null,
  section: null,
  snippet: "…",
  score,
});

describe("arrangeSources", () => {
  const sources = [src(1, 0.9), src(2, 0.05), src(3, 0.6), src(4, 0.8)];

  it("puts cited sources first, then relevant uncited ones, and collapses low relevance", () => {
    const { main, others } = arrangeSources(sources, [3, 1], "qa", false);
    expect(main.map((s) => s.n)).toEqual([3, 1, 4]);
    expect(others.map((s) => s.n)).toEqual([2]);
  });

  it("keeps the original order while the answer is still streaming", () => {
    const { main, others } = arrangeSources(sources, [], "qa", true);
    expect(main.map((s) => s.n)).toEqual([1, 2, 3, 4]);
    expect(others).toEqual([]);
  });

  it("collapses every uncited section of a summary", () => {
    const { main, others } = arrangeSources(
      [src(1, 1), src(2, 1), src(3, 1)],
      [2],
      "summary",
      false,
    );
    expect(main.map((s) => s.n)).toEqual([2]);
    expect(others.map((s) => s.n)).toEqual([1, 3]);
  });
});
