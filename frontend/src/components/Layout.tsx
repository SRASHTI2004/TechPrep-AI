import { FileText, LogOut, MessageSquare, ShieldCheck } from "lucide-react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { cn } from "../lib/utils";
import { ThemeToggle } from "../theme/ThemeToggle";
import { Logo, LogoMark } from "./Logo";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Skeleton } from "./ui/skeleton";

const NAV = [
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/documents", label: "Documents", icon: FileText },
];

function SessionLoading() {
  return (
    <div className="grid min-h-dvh place-items-center" role="status" aria-label="Loading">
      <div className="flex flex-col items-center gap-4">
        <LogoMark className="size-11 animate-pulse" />
        <Skeleton className="h-2 w-28" />
      </div>
    </div>
  );
}

export default function Layout() {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) return <SessionLoading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="flex h-dvh flex-col">
      <header className="z-30 flex h-14 shrink-0 items-center gap-2 border-b bg-card/80 px-3 backdrop-blur supports-[backdrop-filter]:bg-card/70 sm:gap-6 sm:px-5">
        <NavLink to="/chat" className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Logo className="hidden sm:flex" />
          <LogoMark className="sm:hidden" />
          <span className="sr-only sm:hidden">TechPrep AI</span>
        </NavLink>

        <nav className="flex items-center gap-1" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              <Icon className="size-4" />
              <span className="sr-only min-[400px]:not-sr-only">{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-9 gap-2 px-1.5 sm:pr-2.5" aria-label="Account menu">
                <span className="grid size-7 place-items-center rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 text-xs font-semibold uppercase text-white">
                  {user.email[0]}
                </span>
                <span className="hidden max-w-[180px] truncate text-foreground md:inline">{user.email}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-60">
              <DropdownMenuLabel>
                <div className="text-xs text-muted-foreground">Signed in as</div>
                <div className="truncate font-medium" title={user.email}>
                  {user.email}
                </div>
                {user.role === "admin" && (
                  <div className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground">
                    <ShieldCheck className="size-3" /> admin
                  </div>
                )}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={logout}>
                <LogOut />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>
      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
