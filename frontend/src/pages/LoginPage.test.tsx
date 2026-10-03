import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../theme/ThemeProvider";
import LoginPage, { TAGLINE } from "./LoginPage";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/auth/login")) return json({ detail: "Incorrect email or password" }, 401);
      if (url.endsWith("/auth/register")) return json({ id: "u1", email: "a@b.co", role: "user", created_at: "" }, 201);
      return new Response("not found", { status: 404 });
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

function renderLogin() {
  return render(
    <ThemeProvider>
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/login"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/chat" element={<p>Chat page</p>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

test("explains the product in one sentence and offers sign in", () => {
  renderLogin();
  expect(screen.getByText(TAGLINE)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Sign in" })).toHaveAttribute("aria-selected", "true");
});

test("shows the server's error when sign in fails", async () => {
  renderLogin();
  await userEvent.type(screen.getByLabelText("Email"), "a@b.co");
  await userEvent.type(screen.getByLabelText("Password"), "wrongpassword");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password");
});

test("switching to create account shows the password rule; the eye toggles visibility", async () => {
  renderLogin();
  await userEvent.click(screen.getByRole("tab", { name: "Create account" }));
  expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
  expect(screen.getByText("At least 8 characters.")).toBeInTheDocument();

  const password = screen.getByLabelText("Password");
  expect(password).toHaveAttribute("type", "password");
  await userEvent.click(screen.getByRole("button", { name: "Show password" }));
  expect(password).toHaveAttribute("type", "text");
});
