import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import ChatPage from "./ChatPage";

function sseResponse(events: [string, unknown][]): Response {
  const text = events.map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join("");
  return new Response(text, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

const json = (body: unknown) =>
  new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });

const source = {
  n: 1,
  chunk_id: "c1",
  document_id: "d1",
  filename: "system_design.md",
  page: null,
  section: "Primer > Database > Sharding",
  snippet: "Sharding distributes data across different databases",
  score: 0.99,
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/conversations")) return json([]);
      if (url.includes("/documents")) return json({ items: [], total: 0 });
      if (url.endsWith("/chat/stream") && init?.method === "POST") {
        return sseResponse([
          ["meta", { conversation_id: "conv-1", user_message_id: "u1", rewritten_question: null }],
          ["sources", [source]],
          ["token", { text: "Sharding splits " }],
          ["token", { text: "data [1]." }],
          [
            "done",
            {
              conversation_id: "conv-1",
              message_id: "a1",
              answered: true,
              citations: [source],
              invalid_citations: [],
              rewritten_question: null,
              provider: "groq",
              model: "m",
              latency: { retrieval_ms: 10, generation_ms: 20, total_ms: 1500 },
            },
          ],
        ]);
      }
      return new Response("not found", { status: 404 });
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

test("streams an answer and shows its cited source in the panel", async () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter
        initialEntries={["/chat"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:conversationId" element={<ChatPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  await userEvent.type(screen.getByLabelText("Your question"), "What is sharding?{Enter}");

  await waitFor(() => expect(screen.getByText(/Sharding splits data/)).toBeInTheDocument());
  expect(screen.getByRole("button", { name: /show source 1/i })).toBeInTheDocument();
  expect(screen.getByText("system_design.md")).toBeInTheDocument();
  expect(screen.getByText(/· cited/)).toBeInTheDocument();
  expect(screen.getByText("1.5s")).toBeInTheDocument();

  const call = vi.mocked(fetch).mock.calls.find(([u]) => String(u).endsWith("/chat/stream"))!;
  expect(JSON.parse(String(call[1]!.body))).toMatchObject({ message: "What is sharding?" });
});
