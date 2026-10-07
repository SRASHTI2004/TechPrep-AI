// Capture the README screenshots from the real production build, with the API mocked.
//
//   npm run build && npm run screenshots
//
// The backend isn't needed: every /api/v1 call is answered here with realistic sample data,
// so the images are reproducible and no LLM is called. Uses the local Chrome if installed,
// otherwise Playwright's Chromium (`npx playwright install chromium`).

import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = resolve(ROOT, "../docs/screenshots");
const PORT = 4183;
const BASE = `http://127.0.0.1:${PORT}`;

// ---------------------------------------------------------------- sample data

const now = Date.now();
const ago = (hours) => new Date(now - hours * 3600_000).toISOString();

const user = { id: "u1", email: "alex@example.com", role: "user", created_at: ago(400) };

const documents = [
  { id: "d1", filename: "system_design_primer.md", content_type: "text/markdown", size_bytes: 412_000, status: "ready", error: null, num_pages: null, num_chunks: 318, created_at: ago(70), updated_at: ago(70) },
  { id: "d2", filename: "databases_lecture_07.pdf", content_type: "application/pdf", size_bytes: 3_480_000, status: "ready", error: null, num_pages: 46, num_chunks: 129, created_at: ago(52), updated_at: ago(52) },
  { id: "d3", filename: "dsa_dynamic_programming.md", content_type: "text/markdown", size_bytes: 96_000, status: "ready", error: null, num_pages: null, num_chunks: 74, created_at: ago(30), updated_at: ago(30) },
  { id: "d4", filename: "os_concurrency_notes.pdf", content_type: "application/pdf", size_bytes: 2_150_000, status: "processing", error: null, num_pages: 31, num_chunks: 0, created_at: ago(0.02), updated_at: ago(0.02) },
  { id: "d5", filename: "scanned_whiteboard.pdf", content_type: "application/pdf", size_bytes: 8_900_000, status: "failed", error: "No extractable text (scanned images only).", num_pages: 12, num_chunks: 0, created_at: ago(5), updated_at: ago(5) },
];

const conversations = [
  { id: "c1", title: "Database sharding trade-offs", created_at: ago(1), updated_at: ago(0.5) },
  { id: "c2", title: "CDN push vs pull", created_at: ago(3), updated_at: ago(3) },
  { id: "c3", title: "0-1 knapsack DP", created_at: ago(26), updated_at: ago(26) },
  { id: "c4", title: "Consistent hashing", created_at: ago(30), updated_at: ago(30) },
  { id: "c5", title: "Summary: databases lecture", created_at: ago(80), updated_at: ago(80) },
  { id: "c6", title: "CAP theorem in practice", created_at: ago(120), updated_at: ago(120) },
  { id: "c7", title: "Write-through vs write-back cache", created_at: ago(300), updated_at: ago(300) },
];

const src = (n, over) => ({
  n,
  chunk_id: `k${n}`,
  document_id: "d1",
  filename: "system_design_primer.md",
  page: null,
  section: null,
  snippet: "",
  score: 0.9,
  cited: true,
  ...over,
});

const sources = [
  src(1, { section: "Primer > Database > Sharding", score: 0.97, snippet: "Sharding distributes data across different databases such that each database can only manage a subset of the data. Common ways to shard a table of users is either through the user's last name initial or the user's geographic location." }),
  src(2, { document_id: "d2", filename: "databases_lecture_07.pdf", page: 14, score: 0.91, snippet: "Disadvantages: you'll need to update your application logic to work with shards, which could result in complex SQL queries. Data distribution can become lopsided in a shard; a set of power users on a shard could result in increased load." }),
  src(3, { section: "Primer > Database > Sharding > Disadvantage(s)", score: 0.88, snippet: "Rebalancing adds additional complexity. A sharding function based on consistent hashing can reduce the amount of transferred data. Joining data from multiple shards is more complex." }),
  src(4, { document_id: "d2", filename: "databases_lecture_07.pdf", page: 15, score: 0.64, snippet: "Sharding adds more hardware and additional complexity. Similar to the advantages of federation, sharding results in less read and write traffic, less replication, and more cache hits." }),
  src(5, { section: "Primer > Database > Federation", score: 0.12, cited: false, snippet: "Federation (or functional partitioning) splits up databases by function. For example, instead of a single, monolithic database, you could have three databases: forums, users, and products." }),
];

const answer = `**Sharding** splits one logical database across many machines, so each shard holds only part of the data [1]. It scales writes, but it comes with real costs:

### Main disadvantages

1. **More complex application logic.** The app (or a routing layer) must know which shard holds a row, and queries can turn into complex SQL [2].
2. **Uneven load ("hot" shards).** Data distribution can become lopsided; a set of power users on one shard increases its load [2].
3. **Rebalancing is hard.** Moving data when you add shards is expensive. Using *consistent hashing* reduces how much data has to move [3].
4. **Cross-shard joins.** Joining data that lives on different shards is slow and complicated [3].

> **Interview tip:** mention that sharding also means more hardware and more operational overhead [4], so reach for read replicas and caching first.`;

const conversation = {
  ...conversations[0],
  messages: [
    { id: "m1", role: "user", content: "What are the disadvantages of sharding?", citations: [], answered: null, feedback: null, created_at: ago(1) },
    {
      id: "m2",
      role: "assistant",
      content: answer,
      citations: sources.filter((s) => s.cited),
      sources,
      mode: "qa",
      answered: true,
      feedback: 1,
      created_at: ago(1),
    },
  ],
};

// ---------------------------------------------------------------- mock API

async function mockApi(page, { docs = documents, convs = conversations } = {}) {
  await page.addInitScript(() => localStorage.setItem("techprep.token", "demo-token"));
  await page.route("**/api/v1/**", (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace("/api/v1", "");
    const json = (body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/auth/me") return json(user);
    if (path === "/documents") return json({ items: docs, total: docs.length });
    if (path === "/conversations") return json(convs);
    if (path === "/conversations/c1") return json(conversation);
    return route.fulfill({ status: 404, contentType: "application/json", body: '{"detail":"not found"}' });
  });
}

async function setTheme(page, theme) {
  await page.addInitScript((t) => localStorage.setItem("techprep.theme", t), theme);
}

async function shot(page, name) {
  await page.waitForTimeout(400); // let enter animations settle
  await page.screenshot({ path: resolve(OUT, `${name}.png`) });
  console.log(`  saved docs/screenshots/${name}.png`);
}

// ---------------------------------------------------------------- run

function startPreview() {
  const proc = spawn("npx", ["vite", "preview", "--port", String(PORT), "--strictPort", "--host", "127.0.0.1"], {
    cwd: ROOT,
    shell: true,
    stdio: "ignore",
  });
  return proc;
}

async function waitForServer() {
  for (let i = 0; i < 60; i++) {
    try {
      if ((await fetch(BASE)).ok) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error("vite preview did not start (did you run `npm run build`?)");
}

async function launch() {
  try {
    return await chromium.launch({ channel: "chrome" });
  } catch {
    return await chromium.launch();
  }
}

const preview = startPreview();
try {
  await waitForServer();
  await mkdir(OUT, { recursive: true });
  const browser = await launch();
  const desktop = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 };

  // 1. Landing / login
  {
    const page = await browser.newPage(desktop);
    await setTheme(page, "light");
    await page.goto(`${BASE}/login`);
    await page.getByRole("heading", { name: "Welcome back" }).waitFor();
    await shot(page, "login");
    await page.close();
  }

  // 2 + 3. Chat with a cited answer, light and dark
  for (const theme of ["light", "dark"]) {
    const page = await browser.newPage(desktop);
    await setTheme(page, theme);
    await mockApi(page);
    await page.goto(`${BASE}/chat/c1`);
    await page.getByText("Main disadvantages").waitFor();
    await page.getByRole("button", { name: /Show source 2/ }).first().click();
    await page.mouse.move(0, 0);
    await shot(page, theme === "light" ? "chat" : "chat-dark");
    await page.close();
  }

  // 4. Documents
  {
    const page = await browser.newPage(desktop);
    await setTheme(page, "light");
    await mockApi(page);
    await page.goto(`${BASE}/documents`);
    await page.getByText("system_design_primer.md").waitFor();
    await shot(page, "documents");
    await page.close();
  }

  // 5. New chat (welcome + suggestions), dark
  {
    const page = await browser.newPage(desktop);
    await setTheme(page, "dark");
    await mockApi(page);
    await page.goto(`${BASE}/chat`);
    await page.getByText("Ask your notes anything").waitFor();
    await shot(page, "new-chat-dark");
    await page.close();
  }

  await browser.close();
} finally {
  preview.kill();
  if (process.platform === "win32") spawn("taskkill", ["/pid", String(preview.pid), "/T", "/F"], { stdio: "ignore" });
}
