import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { Citation } from "../api/types";
import AnswerMarkdown from "./AnswerMarkdown";

const source = (n: number, page: number | null = null): Citation => ({
  n,
  chunk_id: `c${n}`,
  document_id: "d1",
  filename: "lecture.pdf",
  page,
  section: null,
  snippet: "…",
  score: 0.9,
});

describe("AnswerMarkdown", () => {
  it("renders citation chips that report clicks, and keeps invalid ones as text", async () => {
    const onClick = vi.fn();
    render(
      <AnswerMarkdown
        text={"**Sharding** splits data [1]. Invented [9]."}
        sources={[source(1, 14)]}
        onCitationClick={onClick}
      />,
    );
    expect(screen.getByText("Sharding").tagName).toBe("STRONG");
    const chip = screen.getByRole("button", { name: /show source 1: lecture\.pdf, p\. 14/i });
    await userEvent.click(chip);
    expect(onClick).toHaveBeenCalledWith(1);
    expect(screen.getByText(/Invented \[9\]/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /source 9/i })).toBeNull();
  });

  it("opens normal links in a new tab", () => {
    render(<AnswerMarkdown text="See [docs](https://example.com)." sources={[]} />);
    const link = screen.getByRole("link", { name: "docs" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });
});

describe("AnswerMarkdown formatting", () => {
  it("renders headings, lists, bold, code and tables instead of raw symbols", () => {
    const { container } = render(
      <AnswerMarkdown
        text={"### Trade-offs\n\n1. **Latency** first\n2. Then `cost`\n\n| A | B |\n|---|---|\n| 1 | 2 |"}
        sources={[]}
      />,
    );
    expect(screen.getByRole("heading", { level: 3, name: "Trade-offs" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Latency").tagName).toBe("STRONG");
    expect(screen.getByText("cost").tagName).toBe("CODE");
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/[#*`|]/);
  });
});
