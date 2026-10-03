import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import type { Citation, ConversationDetail } from "../api/types";
import ChatPage from "./ChatPage";

function sseResponse(events: [string, unknown][]): Response {
  const text = events.map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join("");
  return new Response(text, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

const json = (body: unknown) =>
  new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });

const source: Citation = {
  n: 1,
  chunk_id: "c1",
  document_id: "d1",
  filename: "system_design.md",
  page: null,
  section: "Primer > Database > Sharding",
  snippet: "Sharding distributes data across different databases",
  score: 0.99,
};

const done = {
  conversation_id: "conv-1",
  message_id: "a1",
  answered: true,
  mode: "qa",
  citations: [source],
  invalid_citations: [],
  rewritten_question: null,
  provider: "groq",
  model: "m",
  latency: { retrieval_ms: 10, generation_ms: 20, total_ms: 1500 },
};

const stored = (id: string, n: number, snippet: string, cited: boolean, score = 0.9): Citation => ({
  ...source,
  n,
  chunk_id: `${id}-c${n}`,
  snippet,
  score,
  cited,
});

// A saved conversation with two answers, each with its own sources.
const HISTORY: ConversationDetail = {
  id: "conv-1",
  title: "Databases",
  created_at: "2026-10-03T10:00:00Z",
  updated_at: "2026-10-03T10:00:00Z",
  messages: [
    { id: "u1", role: "user", content: "What is sharding?", citations: [], answered: null, feedback: null, created_at: "" },
    {
      id: "a1",
      role: "assistant",
      content: "Sharding splits data 【1】.",
      citations: [stored("a1", 1, "Sharding passage", true)],
      sources: [stored("a1", 1, "Sharding passage", true), stored("a1", 2, "Weak passage", false, 0.05)],
      mode: "qa",
      answered: true,
      feedback: null,
      created_at: "",
    },
    { id: "u2", role: "user", content: "What is replication?", citations: [], answered: null, feedback: null, created_at: "" },
    {
      id: "a2",
      role: "assistant",
      content: "Replicas copy writes [1].",
      citations: [stored("a2", 1, "Replication passage", true)],
      sources: [stored("a2", 1, "Replication passage", true)],
      mode: "qa",
      answered: true,
      feedback: null,
      created_at: "",
    },
  ],
};

let streamEvents: [string, unknown][];

beforeEach(() => {
  streamEvents = [
    ["meta", { conversation_id: "conv-1", user_message_id: "u1", rewritten_question: null, mode: "qa" }],
    ["sources", [source]],
    ["token", { text: "Sharding splits " }],
    ["token", { text: "data 【1】." }],
    ["done", done],
  ];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.endsWith("/conversations") && method === "GET")
        return json([{ id: "conv-1", title: "Databases", created_at: "", updated_at: "" }]);
      if (url.endsWith("/conversations/conv-1") && method === "GET") return json(HISTORY);
      if (url.endsWith("/conversations/conv-1") && method === "PATCH")
        return json({ ...HISTORY, title: JSON.parse(String(init!.body)).title });
      if (url.endsWith("/conversations/conv-1") && method === "DELETE")
        return new Response(null, { status: 204 });
      if (url.includes("/documents"))
        return json({
          items: [
            {
              id: "d1",
              filename: "system_design.md",
              content_type: "text/markdown",
              size_bytes: 10,
              status: "ready",
              error: null,
              num_pages: null,
              num_chunks: 3,
              created_at: "",
              updated_at: "",
            },
          ],
          total: 1,
        });
      if (url.endsWith("/chat/stream") && method === "POST") return sseResponse(streamEvents);
      return new Response("not found", { status: 404 });
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:conversationId" element={<ChatPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const streamBody = () => {
  const call = vi.mocked(fetch).mock.calls.find(([u]) => String(u).endsWith("/chat/stream"))!;
  return JSON.parse(String(call[1]!.body));
};

test("streams an answer and shows its cited source in the panel", async () => {
  renderAt("/chat");
  await userEvent.type(screen.getByLabelText("Your question"), "What is sharding?{Enter}");

  // 【1】 from the model is shown as a normal, clickable citation chip.
  await waitFor(() => expect(screen.getByText(/Sharding splits data/)).toBeInTheDocument());
  expect(screen.queryByText(/【/)).toBeNull();
  expect(screen.getByRole("button", { name: /show source 1/i })).toBeInTheDocument();
  const panel = within(document.querySelector<HTMLElement>("aside.sources")!);
  expect(panel.getByText("system_design.md")).toBeInTheDocument();
  expect(screen.getByText(/· cited/)).toBeInTheDocument();
  expect(screen.getByText("1.5s")).toBeInTheDocument();
  expect(streamBody()).toMatchObject({ message: "What is sharding?", mode: "auto" });
});

test("a loaded conversation shows the sources of whichever answer is selected", async () => {
  renderAt("/chat/conv-1");
  // Default: the latest answer's sources.
  await waitFor(() => expect(screen.getByText(/Replication passage/)).toBeInTheDocument());
  expect(screen.getByText(/For: “What is replication\?”/)).toBeInTheDocument();

  // Select the first answer: its own sources come back, cited first, weak one collapsed.
  await userEvent.click(screen.getByText(/Sharding splits data/));
  expect(screen.getByText(/Sharding passage/)).toBeInTheDocument();
  expect(screen.queryByText(/Replication passage/)).toBeNull();
  expect(screen.getByText(/For: “What is sharding\?”/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Other retrieved passages \(1\)/ })).toBeInTheDocument();
});

test("clicking a citation chip highlights its source", async () => {
  renderAt("/chat/conv-1");
  await waitFor(() => expect(screen.getByText(/Sharding splits data/)).toBeInTheDocument());
  const chips = screen.getAllByRole("button", { name: /show source 1/i });
  await userEvent.click(chips[0]!);
  const card = screen.getByText(/Sharding passage/).closest("li")!;
  expect(card).toHaveClass("active");
});

test("copy, rename and delete", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  renderAt("/chat/conv-1");
  await waitFor(() => expect(screen.getByText(/Sharding splits data/)).toBeInTheDocument());

  await userEvent.click(screen.getAllByRole("button", { name: "Copy answer" })[0]!);
  expect(writeText).toHaveBeenCalledWith("Sharding splits data [1].");
  expect(screen.getByText("Copied!")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Rename conversation Databases" }));
  const input = screen.getByLabelText("Chat name");
  await userEvent.clear(input);
  await userEvent.type(input, "Sharding notes{Enter}");
  await waitFor(() =>
    expect(
      vi.mocked(fetch).mock.calls.some(
        ([u, i]) => String(u).endsWith("/conversations/conv-1") && i?.method === "PATCH",
      ),
    ).toBe(true),
  );

  await userEvent.click(screen.getByRole("button", { name: /Delete conversation/ }));
  expect(window.confirm).toHaveBeenCalled();
  await waitFor(() =>
    expect(
      vi.mocked(fetch).mock.calls.some(
        ([u, i]) => String(u).endsWith("/conversations/conv-1") && i?.method === "DELETE",
      ),
    ).toBe(true),
  );
});

test("Summarize sends a summary request and shows progress", async () => {
  streamEvents = [
    ["meta", { conversation_id: "conv-2", user_message_id: "u9", rewritten_question: null, mode: "summary" }],
    ["sources", [source]],
    ["status", { text: "Reading part 1 of 2…" }],
    ["token", { text: "Overview [1]." }],
    ["done", { ...done, conversation_id: "conv-2", mode: "summary" }],
  ];
  renderAt("/chat");
  await waitFor(() => expect(screen.getByRole("button", { name: "Summarize all" })).toBeEnabled());
  await userEvent.click(screen.getByRole("button", { name: "Summarize all" }));

  await waitFor(() => expect(screen.getByText(/Overview/)).toBeInTheDocument());
  expect(streamBody()).toMatchObject({ mode: "summary", document_ids: null });
  expect(screen.getByText("summary")).toBeInTheDocument();
  expect(screen.getByText(/document section · cited/)).toBeInTheDocument();
});
