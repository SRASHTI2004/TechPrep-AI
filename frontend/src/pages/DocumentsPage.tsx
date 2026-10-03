import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileText,
  FileType2,
  Layers,
  Loader2,
  RotateCcw,
  Sparkles,
  Trash2,
  UploadCloud,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { documentsApi } from "../api/endpoints";
import type { DocumentItem, DocumentStatus } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { Badge } from "../components/ui/badge";
import type { BadgeProps } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { EmptyState } from "../components/ui/empty-state";
import { Skeleton } from "../components/ui/skeleton";
import { cn } from "../lib/utils";
import type { SummarizeRequest } from "./ChatPage";

const ACCEPT = ".pdf,.md,.markdown,.txt";
const STATUS: Record<
  DocumentStatus,
  { label: string; variant: BadgeProps["variant"]; icon: typeof Clock; spin?: boolean }
> = {
  pending: { label: "Queued", variant: "warning", icon: Clock },
  processing: { label: "Processing…", variant: "warning", icon: Loader2, spin: true },
  ready: { label: "Ready", variant: "success", icon: CheckCircle2 },
  failed: { label: "Failed", variant: "destructive", icon: XCircle },
};
// Name, status, pages, chunks, size, uploaded, actions.
const ROW_GRID = "md:grid md:grid-cols-[minmax(0,1fr)_120px_64px_72px_80px_104px_196px] md:items-center md:gap-4";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function FileIcon({ filename }: { filename: string }) {
  const pdf = filename.toLowerCase().endsWith(".pdf");
  const Icon = pdf ? FileType2 : FileText;
  return (
    <span
      className={cn(
        "grid size-9 shrink-0 place-items-center rounded-lg",
        pdf ? "bg-rose-500/10 text-rose-600 dark:text-rose-400" : "bg-sky-500/10 text-sky-600 dark:text-sky-400",
      )}
    >
      <Icon className="size-4" />
    </span>
  );
}

function StatusBadge({ status }: { status: DocumentStatus }) {
  const s = STATUS[status];
  return (
    <Badge variant={s.variant}>
      <s.icon className={cn(s.spin && "animate-spin")} />
      {s.label}
    </Badge>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof Clock; label: string; value: number | string }) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <span className="grid size-9 place-items-center rounded-lg bg-accent text-accent-foreground">
        <Icon className="size-4" />
      </span>
      <div>
        <div className="text-xl font-semibold tabular-nums leading-tight">{value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
    </Card>
  );
}

function ListSkeleton() {
  return (
    <ul aria-label="Loading documents" className="divide-y">
      {Array.from({ length: 4 }, (_, i) => (
        <li key={i} className="flex items-center gap-3 px-4 py-4">
          <Skeleton className="size-9 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-2/5" />
            <Skeleton className="h-3 w-1/4" />
          </div>
          <Skeleton className="hidden h-5 w-16 rounded-full sm:block" />
          <Skeleton className="hidden h-8 w-24 md:block" />
        </li>
      ))}
    </ul>
  );
}

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState<string[]>([]);
  const [toDelete, setToDelete] = useState<DocumentItem | null>(null);

  const docs = useQuery({
    queryKey: ["documents"],
    queryFn: documentsApi.list,
    // Poll while anything is still being ingested in the background.
    refetchInterval: (q) =>
      q.state.data?.items.some((d) => d.status === "pending" || d.status === "processing")
        ? 1500
        : false,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["documents"] });
  const upload = useMutation({ mutationFn: documentsApi.upload, onSettled: invalidate });
  const remove = useMutation({
    mutationFn: documentsApi.remove,
    onSettled: invalidate,
    onError: (err) => toast.error("Could not delete the document", { description: err.message }),
  });
  const reingest = useMutation({
    mutationFn: documentsApi.reingest,
    onSettled: invalidate,
    onSuccess: (d) => toast.info(`Retrying ${d.filename}`),
    onError: (err) => toast.error("Could not retry", { description: err.message }),
  });

  // Tell the user when background ingestion finishes (seen as a status change while polling).
  const lastStatus = useRef(new Map<string, DocumentStatus>());
  useEffect(() => {
    for (const d of docs.data?.items ?? []) {
      const before = lastStatus.current.get(d.id);
      if (before && before !== d.status) {
        if (d.status === "ready") toast.success(`${d.filename} is ready`, { description: `${d.num_chunks} chunks indexed. You can chat with it now.` });
        if (d.status === "failed") toast.error(`${d.filename} failed to process`, { description: d.error ?? undefined });
      }
      lastStatus.current.set(d.id, d.status);
    }
  }, [docs.data]);

  async function handleFiles(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      setUploading((u) => [...u, file.name]);
      try {
        await upload.mutateAsync(file);
        toast.success(`Uploaded ${file.name}`, { description: "Processing in the background." });
      } catch (err) {
        toast.error(`Could not upload ${file.name}`, { description: (err as Error).message });
      } finally {
        setUploading((u) => u.filter((n) => n !== file.name));
      }
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) void handleFiles(e.dataTransfer.files);
  }

  const items = docs.data?.items ?? [];
  const ready = items.filter((d) => d.status === "ready");
  const openPicker = () => inputRef.current?.click();

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
        <PageHeader
          title="Documents"
          description="Upload notes or PDFs (.pdf, .md, .txt, max 20 MB). Only you can search your documents."
          actions={
            <Button onClick={openPicker} disabled={uploading.length > 0}>
              <UploadCloud /> Upload
            </Button>
          }
        />

        {items.length > 0 && (
          <div className="grid grid-cols-3 gap-3 sm:gap-4">
            <Stat icon={FileText} label="Documents" value={items.length} />
            <Stat icon={CheckCircle2} label="Ready to chat" value={ready.length} />
            <Stat icon={Layers} label="Indexed chunks" value={ready.reduce((n, d) => n + d.num_chunks, 0)} />
          </div>
        )}

        <div
          className={cn(
            "group flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed bg-card/60 px-6 py-8 text-center transition-colors hover:border-primary/60 hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            dragging && "border-primary bg-accent",
          )}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={openPicker}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && openPicker()}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            multiple
            hidden
            data-testid="file-input"
            onChange={(e) => {
              if (e.target.files) void handleFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <span className="grid size-11 place-items-center rounded-full bg-accent text-accent-foreground transition-transform group-hover:-translate-y-0.5">
            {uploading.length ? <Loader2 className="size-5 animate-spin" /> : <UploadCloud className="size-5" />}
          </span>
          <strong className="text-sm font-semibold">
            {uploading.length ? `Uploading ${uploading.join(", ")}…` : "Drop files here or click to upload"}
          </strong>
          <span className="text-xs text-muted-foreground">
            Text is extracted, chunked and embedded in the background.
          </span>
        </div>

        <Card className="overflow-hidden">
          {items.length > 0 && (
            <div className={cn("hidden border-b bg-muted/40 px-4 py-2.5 text-xs font-medium text-muted-foreground", ROW_GRID)}>
              <span>Name</span>
              <span>Status</span>
              <span>Pages</span>
              <span>Chunks</span>
              <span>Size</span>
              <span>Uploaded</span>
              <span className="sr-only">Actions</span>
            </div>
          )}

          {docs.isLoading ? (
            <ListSkeleton />
          ) : docs.isError ? (
            <EmptyState
              tone="error"
              icon={AlertTriangle}
              title="Could not load documents"
              description={(docs.error as Error).message}
              action={
                <Button variant="outline" onClick={() => void docs.refetch()}>
                  <RotateCcw /> Try again
                </Button>
              }
            />
          ) : items.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No documents yet"
              description="Upload your study notes or a lecture PDF to start chatting. Answers will cite the exact page they came from."
              action={
                <Button onClick={openPicker}>
                  <UploadCloud /> Upload your first document
                </Button>
              }
            />
          ) : (
            <ul className="divide-y">
              {items.map((d) => (
                <li key={d.id} className={cn("flex flex-col gap-3 px-4 py-3.5 transition-colors hover:bg-muted/30", ROW_GRID)}>
                  <div className="flex min-w-0 items-center gap-3">
                    <FileIcon filename={d.filename} />
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium" title={d.filename}>
                        {d.filename}
                      </div>
                      <div className="text-xs text-muted-foreground md:hidden">
                        {formatSize(d.size_bytes)} · {new Date(d.created_at).toLocaleDateString()}
                        {d.status === "ready" && ` · ${d.num_chunks} chunks`}
                      </div>
                      {d.error && <div className="mt-0.5 line-clamp-2 text-xs text-destructive">{d.error}</div>}
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-2 md:contents">
                    <span>
                      <StatusBadge status={d.status} />
                    </span>
                    <span className="hidden text-sm tabular-nums text-muted-foreground md:block">{d.num_pages ?? "—"}</span>
                    <span className="hidden text-sm tabular-nums text-muted-foreground md:block">
                      {d.status === "ready" ? d.num_chunks : "—"}
                    </span>
                    <span className="hidden text-sm tabular-nums text-muted-foreground md:block">{formatSize(d.size_bytes)}</span>
                    <span className="hidden text-sm text-muted-foreground md:block">
                      {new Date(d.created_at).toLocaleDateString()}
                    </span>
                    <div className="flex items-center justify-end gap-1">
                      {d.status === "ready" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={`Summarize ${d.filename}`}
                          onClick={() => {
                            const state: SummarizeRequest = {
                              summarize: { id: d.id, filename: d.filename },
                            };
                            navigate("/chat", { state });
                          }}
                        >
                          <Sparkles /> Summarize
                        </Button>
                      )}
                      {d.status === "failed" && (
                        <Button variant="ghost" size="sm" onClick={() => reingest.mutate(d.id)}>
                          <RotateCcw /> Retry
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="hover:bg-destructive/10 hover:text-destructive"
                        aria-label={`Delete ${d.filename}`}
                        title="Delete"
                        onClick={() => setToDelete(d)}
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(open) => !open && setToDelete(null)}
        title="Delete this document?"
        description={`"${toDelete?.filename ?? ""}" and all its chunks will be removed. This cannot be undone.`}
        onConfirm={() => {
          if (!toDelete) return;
          const name = toDelete.filename;
          remove.mutate(toDelete.id, { onSuccess: () => toast.success(`Deleted ${name}`) });
        }}
      />
    </div>
  );
}
