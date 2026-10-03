import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { Citation } from "../api/types";
import SourcesPanel from "./SourcesPanel";

const src = (n: number, score: number, snippet: string): Citation => ({
  n,
  chunk_id: `c${n}`,
  document_id: "d1",
  filename: "notes.md",
  page: null,
  section: null,
  snippet,
  score,
});

const sources = [src(1, 0.9, "Cited passage"), src(2, 0.02, "Weak passage")];

describe("SourcesPanel", () => {
  it("shows cited sources and hides low-relevance ones under a toggle", async () => {
    render(<SourcesPanel sources={sources} cited={[1]} active={null} onSelect={() => {}} />);
    expect(screen.getByText(/Cited passage/)).toBeInTheDocument();
    expect(screen.queryByText(/Weak passage/)).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: /Other retrieved passages \(1\)/ }));
    expect(screen.getByText(/Weak passage/)).toBeInTheDocument();
    expect(screen.getByText(/· not cited/)).toBeInTheDocument();
  });

  it("opens the collapsed group when its source becomes active", () => {
    render(<SourcesPanel sources={sources} cited={[1]} active={2} onSelect={() => {}} />);
    expect(screen.getByText(/Weak passage/)).toBeInTheDocument();
  });

  it("labels summary sections instead of showing a relevance score", () => {
    render(
      <SourcesPanel
        sources={[src(1, 1, "Section text")]}
        cited={[1]}
        active={null}
        onSelect={() => {}}
        mode="summary"
        label="Summarize notes.md"
      />,
    );
    expect(screen.getByText(/document section · cited/)).toBeInTheDocument();
    expect(screen.getByText(/For: “Summarize notes.md”/)).toBeInTheDocument();
  });
});
