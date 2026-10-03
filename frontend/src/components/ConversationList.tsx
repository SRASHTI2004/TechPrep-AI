import { AlertTriangle, MessageSquare, MessagesSquare, Pencil, Plus, RotateCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import type { Conversation } from "../api/types";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";

function ConversationItem({
  conversation: c,
  active,
  onRename,
  onDelete,
  onNavigate,
}: {
  conversation: Conversation;
  active: boolean;
  onRename: (title: string) => void;
  onDelete: () => void;
  onNavigate?: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(c.title);

  if (editing) {
    const save = () => {
      const t = title.trim();
      if (t && t !== c.title) onRename(t);
      setEditing(false);
    };
    return (
      <li className="px-1 py-0.5">
        <Input
          className="h-8 text-sm"
          value={title}
          maxLength={200}
          autoFocus
          aria-label="Chat name"
          onChange={(e) => setTitle(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => {
            if (e.key === "Enter") save();
            if (e.key === "Escape") {
              setTitle(c.title);
              setEditing(false);
            }
          }}
        />
      </li>
    );
  }

  return (
    <li
      className={cn(
        "group/item relative flex items-center rounded-lg transition-colors",
        active ? "bg-accent text-accent-foreground" : "hover:bg-muted",
      )}
    >
      <Link
        to={`/chat/${c.id}`}
        title={c.title}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        className="flex min-w-0 flex-1 items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <MessageSquare className={cn("size-3.5 shrink-0", active ? "text-primary" : "text-muted-foreground")} />
        <span className={cn("truncate", active && "font-medium")}>{c.title}</span>
      </Link>
      <div className="flex shrink-0 items-center pr-1 opacity-100 transition-opacity lg:opacity-0 lg:group-focus-within/item:opacity-100 lg:group-hover/item:opacity-100">
        <Button
          variant="ghost"
          size="icon-sm"
          className="size-7"
          aria-label={`Rename conversation ${c.title}`}
          title="Rename"
          onClick={() => {
            setTitle(c.title);
            setEditing(true);
          }}
        >
          <Pencil className="!size-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          className="size-7 hover:bg-destructive/10 hover:text-destructive"
          aria-label={`Delete conversation ${c.title}`}
          title="Delete"
          onClick={onDelete}
        >
          <Trash2 className="!size-3.5" />
        </Button>
      </div>
    </li>
  );
}

const DAY = 24 * 60 * 60 * 1000;

/** "Today", "Yesterday", "Previous 7 days", "Older" by last activity. */
function groupByRecency(conversations: Conversation[], now = new Date()): [string, Conversation[]][] {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const groups = new Map<string, Conversation[]>();
  for (const c of conversations) {
    const t = new Date(c.updated_at).getTime();
    const label = Number.isNaN(t)
      ? "Older"
      : t >= startOfToday
        ? "Today"
        : t >= startOfToday - DAY
          ? "Yesterday"
          : t >= startOfToday - 7 * DAY
            ? "Previous 7 days"
            : "Older";
    groups.set(label, [...(groups.get(label) ?? []), c]);
  }
  return ["Today", "Yesterday", "Previous 7 days", "Older"]
    .filter((l) => groups.has(l))
    .map((l) => [l, groups.get(l)!]);
}

interface Props {
  conversations: Conversation[] | undefined;
  isLoading: boolean;
  error: Error | null;
  onRetry: () => void;
  activeId: string | null;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (conversation: Conversation) => void;
  /** Called after a conversation link is followed (closes the mobile sheet). */
  onNavigate?: () => void;
}

export default function ConversationList({
  conversations,
  isLoading,
  error,
  onRetry,
  activeId,
  onNew,
  onRename,
  onDelete,
  onNavigate,
}: Props) {
  return (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <Button className="w-full" onClick={onNew}>
          <Plus /> New chat
        </Button>
      </div>
      <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-3" aria-label="Conversations">
        {isLoading ? (
          <div className="space-y-1 px-1" aria-label="Loading conversations">
            <Skeleton className="mb-3 mt-2 h-2.5 w-14" />
            {[70, 55, 85, 60, 45].map((w, i) => (
              <div key={i} className="flex items-center gap-2.5 px-1.5 py-2">
                <Skeleton className="size-3.5 rounded" />
                <Skeleton className="h-3" style={{ width: `${w}%` }} />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="mx-1 mt-2 rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-xs" role="alert">
            <div className="flex items-center gap-1.5 font-medium text-destructive">
              <AlertTriangle className="size-3.5" /> Could not load chats
            </div>
            <p className="mt-1 text-muted-foreground">{error.message}</p>
            <Button variant="outline" size="sm" className="mt-2.5 h-7" onClick={onRetry}>
              <RotateCcw /> Retry
            </Button>
          </div>
        ) : !conversations?.length ? (
          <div className="mx-1 mt-2 flex flex-col items-center rounded-lg border border-dashed px-4 py-8 text-center">
            <MessagesSquare className="mb-2 size-5 text-muted-foreground" />
            <p className="text-sm font-medium">No chats yet</p>
            <p className="mt-0.5 text-xs text-muted-foreground">Your conversations will appear here.</p>
          </div>
        ) : (
          groupByRecency(conversations).map(([label, items]) => (
            <div key={label} className="mb-3">
              <h3 className="px-2.5 pb-1 pt-2 text-[0.7rem] font-semibold uppercase tracking-wider text-muted-foreground">
                {label}
              </h3>
              <ul className="space-y-0.5">
                {items.map((c) => (
                  <ConversationItem
                    key={c.id}
                    conversation={c}
                    active={c.id === activeId}
                    onRename={(title) => onRename(c.id, title)}
                    onDelete={() => onDelete(c)}
                    onNavigate={onNavigate}
                  />
                ))}
              </ul>
            </div>
          ))
        )}
      </nav>
    </div>
  );
}
