import { AlertCircle, ArrowRight, BookOpenCheck, Eye, EyeOff, Loader2, Quote, SearchCheck, ShieldQuestion } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input, Label } from "../components/ui/input";
import { cn } from "../lib/utils";
import { ThemeToggle } from "../theme/ThemeToggle";

export const TAGLINE =
  "TechPrep AI answers questions from your own interview-prep notes and PDFs, cites the exact page behind every claim, and says “I don't know” instead of guessing.";

const FEATURES = [
  {
    icon: SearchCheck,
    title: "Hybrid retrieval",
    text: "Semantic + keyword search, reranked by a cross-encoder.",
  },
  {
    icon: BookOpenCheck,
    title: "Page-level citations",
    text: "Every claim links to the file, page and section it came from.",
  },
  {
    icon: ShieldQuestion,
    title: "No guessing",
    text: "If your notes don't cover it, you get “I don't know”.",
  },
];

/** A static mock of an answer, to show what the product does at a glance. */
function AnswerPreview() {
  return (
    <div className="relative mt-10 hidden lg:block" aria-hidden>
      <div className="absolute -inset-4 -z-10 rounded-3xl bg-gradient-to-tr from-indigo-500/15 via-violet-500/10 to-transparent blur-2xl" />
      <Card className="max-w-lg p-5 shadow-lifted">
        <div className="mb-3 ml-auto w-fit rounded-2xl rounded-br-md bg-primary px-3.5 py-2 text-sm text-primary-foreground">
          What are the downsides of sharding?
        </div>
        <div className="space-y-2 text-sm leading-relaxed">
          <p>
            <strong>Sharding</strong> adds operational complexity:
          </p>
          <ul className="list-disc space-y-1 pl-5 marker:text-muted-foreground">
            <li>
              Joins across shards become expensive
              <Chip n={1} />
            </li>
            <li>
              Uneven data can create <em>hot</em> shards
              <Chip n={2} />
            </li>
          </ul>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 border-t pt-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5 rounded-md border bg-muted/50 px-2 py-1">
            <Chip n={1} /> system_design.md › Sharding
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-md border bg-muted/50 px-2 py-1">
            <Chip n={2} /> databases.pdf, p. 14
          </span>
        </div>
      </Card>
    </div>
  );
}

function Chip({ n }: { n: number }) {
  return (
    <span className="mx-0.5 inline-grid h-[1.15rem] min-w-[1.15rem] place-items-center rounded-md bg-accent px-1 align-[0.1em] text-[0.68rem] font-semibold text-accent-foreground ring-1 ring-inset ring-primary/20">
      {n}
    </span>
  );
}

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const from = (location.state as { from?: string } | null)?.from ?? "/chat";
  if (user) return <Navigate to={from} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const tab = (value: "login" | "register", label: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={mode === value}
      onClick={() => {
        setMode(value);
        setError(null);
      }}
      className={cn(
        "flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-all",
        mode === value
          ? "bg-card text-foreground shadow-sm"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );

  return (
    <div className="relative min-h-dvh overflow-hidden">
      {/* Soft brand glow + faint grid behind everything. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_50%_at_20%_0%,hsl(var(--primary)/0.14),transparent_70%),radial-gradient(40%_40%_at_100%_100%,hsl(270_80%_60%/0.10),transparent_70%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.35] [background-image:linear-gradient(hsl(var(--border))_1px,transparent_1px),linear-gradient(90deg,hsl(var(--border))_1px,transparent_1px)] [background-size:44px_44px] [mask-image:radial-gradient(ellipse_at_top,black_20%,transparent_70%)]"
      />

      <header className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <ThemeToggle />
      </header>

      <main className="mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-6 sm:px-6 lg:grid-cols-[1.15fr_1fr] lg:gap-16 lg:pt-12">
        <section>
          <span className="inline-flex items-center gap-1.5 rounded-full border bg-card/70 px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm backdrop-blur">
            <Quote className="size-3 text-primary" /> Grounded answers · cited sources
          </span>
          <h1 className="mt-5 text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
            Study from <span className="bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">your own notes</span>, with
            receipts.
          </h1>
          <p className="mt-4 max-w-xl text-pretty text-base text-muted-foreground sm:text-lg">{TAGLINE}</p>

          <ul className="mt-8 grid gap-4 sm:grid-cols-3 lg:max-w-2xl">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-3 sm:flex-col sm:gap-2">
                <span className="grid size-9 shrink-0 place-items-center rounded-lg border bg-card text-primary shadow-sm">
                  <Icon className="size-4" />
                </span>
                <div>
                  <div className="text-sm font-semibold">{title}</div>
                  <div className="text-sm text-muted-foreground">{text}</div>
                </div>
              </li>
            ))}
          </ul>

          <AnswerPreview />
        </section>

        <Card className="w-full p-6 shadow-lifted sm:p-8 lg:max-w-md lg:justify-self-end">
          <form onSubmit={onSubmit} className="flex flex-col gap-5">
            <div>
              <h2 className="text-xl font-semibold tracking-tight">
                {mode === "login" ? "Welcome back" : "Create your account"}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {mode === "login"
                  ? "Sign in to chat with your documents."
                  : "Free and private: only you can search your documents."}
              </p>
            </div>

            <div className="flex gap-1 rounded-lg bg-muted p-1" role="tablist">
              {tab("login", "Sign in")}
              {tab("register", "Create account")}
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  required
                  minLength={8}
                  className="pr-10"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 grid w-10 place-items-center rounded-r-lg text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {mode === "register" && (
                <p className="text-xs text-muted-foreground">At least 8 characters.</p>
              )}
            </div>

            {error && (
              <div
                className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
                role="alert"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                {error}
              </div>
            )}

            <Button type="submit" size="lg" disabled={busy} className="w-full">
              {busy ? (
                <>
                  <Loader2 className="animate-spin" /> Please wait…
                </>
              ) : (
                <>
                  {mode === "login" ? "Sign in" : "Create account"} <ArrowRight />
                </>
              )}
            </Button>
          </form>
        </Card>
      </main>
    </div>
  );
}
