import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../lib/utils";

interface Props {
  icon: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  tone?: "default" | "error";
  className?: string;
}

/** Centered icon + message + optional action, for empty lists and failed loads. */
export function EmptyState({ icon: Icon, title, description, action, tone = "default", className }: Props) {
  return (
    <div
      className={cn("flex flex-col items-center justify-center px-6 py-12 text-center", className)}
      role={tone === "error" ? "alert" : undefined}
    >
      <div
        className={cn(
          "mb-4 grid size-12 place-items-center rounded-xl border shadow-sm",
          tone === "error"
            ? "border-destructive/20 bg-destructive/10 text-destructive"
            : "bg-card text-primary",
        )}
      >
        <Icon className="size-5" />
      </div>
      <h3 className="text-base font-semibold">{title}</h3>
      {description && (
        <div className="mt-1.5 max-w-sm text-sm text-muted-foreground">{description}</div>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
