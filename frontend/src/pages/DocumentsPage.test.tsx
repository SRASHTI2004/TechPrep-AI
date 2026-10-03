import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "sonner";

import type { DocumentItem } from "../api/types";
import DocumentsPage from "./DocumentsPage";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const doc = (over: Partial<DocumentItem>): DocumentItem => ({
  id: "d1",
  filename: "system_design.md",
  content_type: "text/markdown",
  size_bytes: 20_480,
  status: "ready",
  error: null,
  num_pages: null,
  num_chunks: 42,
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:00:00Z",
  ...over,
});

let listResponse: () => Response;

beforeEach(() => {
  listResponse = () => json({ items: [], total: 0 });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/documents?") && method === "GET") return listResponse();
      if (url.endsWith("/documents") && method === "POST")
        return json({ detail: "Unsupported file type" }, 415);
      if (url.endsWith("/documents/d1") && method === "DELETE") return new Response(null, { status: 204 });
      return new Response("not found", { status: 404 });
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DocumentsPage />
        <Toaster />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

test("shows a skeleton while loading, then a helpful empty state", async () => {
  renderPage();
  expect(screen.getByLabelText("Loading documents")).toBeInTheDocument();
  expect(await screen.findByText("No documents yet")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Upload your first document/ })).toBeInTheDocument();
});

test("lists documents with their status and stats", async () => {
  listResponse = () =>
    json({
      items: [
        doc({}),
        doc({ id: "d2", filename: "lecture.pdf", status: "processing", num_chunks: 0 }),
        doc({ id: "d3", filename: "broken.pdf", status: "failed", error: "No text found" }),
      ],
      total: 3,
    });
  renderPage();
  expect(await screen.findByText("system_design.md")).toBeInTheDocument();
  expect(screen.getByText("Ready")).toBeInTheDocument();
  expect(screen.getByText("Processing…")).toBeInTheDocument();
  expect(screen.getByText("No text found")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Summarize system_design.md" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Retry/ })).toBeInTheDocument();
  expect(screen.getByText("Ready to chat").previousSibling).toHaveTextContent("1");
});

test("a failed upload shows an error toast", async () => {
  renderPage();
  await screen.findByText("No documents yet");
  const file = new File(["x"], "photo.png", { type: "image/png" });
  await userEvent.upload(screen.getByTestId("file-input"), file, { applyAccept: false });
  expect(await screen.findByText("Could not upload photo.png")).toBeInTheDocument();
  expect(screen.getByText("Unsupported file type")).toBeInTheDocument();
});

test("delete asks for confirmation, then deletes", async () => {
  listResponse = () => json({ items: [doc({})], total: 1 });
  renderPage();
  await userEvent.click(await screen.findByRole("button", { name: "Delete system_design.md" }));

  const dialog = await screen.findByRole("alertdialog");
  expect(within(dialog).getByText(/system_design\.md/)).toBeInTheDocument();
  await userEvent.click(within(dialog).getByRole("button", { name: "Delete" }));

  await waitFor(() =>
    expect(
      vi.mocked(fetch).mock.calls.some(
        ([u, i]) => String(u).endsWith("/documents/d1") && i?.method === "DELETE",
      ),
    ).toBe(true),
  );
  expect(await screen.findByText("Deleted system_design.md")).toBeInTheDocument();
});

test("a failed load shows an error state with retry", async () => {
  listResponse = () => json({ detail: "Database unavailable" }, 503);
  renderPage();
  expect(await screen.findByText("Could not load documents")).toBeInTheDocument();
  expect(screen.getByText("Database unavailable")).toBeInTheDocument();

  listResponse = () => json({ items: [doc({})], total: 1 });
  await userEvent.click(screen.getByRole("button", { name: /Try again/ }));
  expect(await screen.findByText("system_design.md")).toBeInTheDocument();
});
