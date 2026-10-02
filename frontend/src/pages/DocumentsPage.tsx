import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import type { DragEvent } from "react";

import { documentsApi } from "../api/endpoints";
import type { DocumentItem, DocumentStatus } from "../api/types";

const ACCEPT = ".pdf,.md,.markdown,.txt";
const STATUS_LABEL: Record<DocumentStatus, string> = {
  pending: "Queued",
  processing: "Processing…",
  ready: "Ready",
  failed: "Failed",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

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
  const remove = useMutation({ mutationFn: documentsApi.remove, onSettled: invalidate });
  const reingest = useMutation({ mutationFn: documentsApi.reingest, onSettled: invalidate });

  async function handleFiles(files: FileList | File[]) {
    setUploadErrors([]);
    for (const file of Array.from(files)) {
      try {
        await upload.mutateAsync(file);
      } catch (err) {
        setUploadErrors((e) => [...e, `${file.name}: ${(err as Error).message}`]);
      }
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) void handleFiles(e.dataTransfer.files);
  }

  function confirmDelete(doc: DocumentItem) {
    if (window.confirm(`Delete "${doc.filename}" and all its chunks?`)) remove.mutate(doc.id);
  }

  const items = docs.data?.items ?? [];

  return (
    <div className="page">
      <div className="page-header">
        <h2>Documents</h2>
        <p className="muted">
          Upload notes or PDFs (.pdf, .md, .txt, max 20 MB). Only you can search your documents.
        </p>
      </div>

      <div
        className={`dropzone${dragging ? " dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
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
        <strong>{upload.isPending ? "Uploading…" : "Drop files here or click to upload"}</strong>
        <span className="muted">Text is extracted, chunked and embedded in the background.</span>
      </div>

      {uploadErrors.map((msg) => (
        <p key={msg} className="error" role="alert">
          {msg}
        </p>
      ))}

      {docs.isLoading ? (
        <p className="muted">Loading documents…</p>
      ) : docs.isError ? (
        <p className="error">Could not load documents: {(docs.error as Error).message}</p>
      ) : items.length === 0 ? (
        <div className="empty">
          <p>No documents yet.</p>
          <p className="muted">Upload your study notes or a lecture PDF to start chatting.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="doc-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Pages</th>
                <th>Chunks</th>
                <th>Size</th>
                <th>Uploaded</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {items.map((d) => (
                <tr key={d.id}>
                  <td className="filename" title={d.filename}>
                    {d.filename}
                  </td>
                  <td>
                    <span className={`status status-${d.status}`}>{STATUS_LABEL[d.status]}</span>
                    {d.error && <div className="error small">{d.error}</div>}
                  </td>
                  <td>{d.num_pages ?? "—"}</td>
                  <td>{d.status === "ready" ? d.num_chunks : "—"}</td>
                  <td>{formatSize(d.size_bytes)}</td>
                  <td>{new Date(d.created_at).toLocaleDateString()}</td>
                  <td className="actions">
                    {d.status === "failed" && (
                      <button className="ghost" onClick={() => reingest.mutate(d.id)}>
                        Retry
                      </button>
                    )}
                    <button className="ghost danger" onClick={() => confirmDelete(d)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
