"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/Spinner";
import { api } from "@/lib/api";

type Attachment = {
  id: number;
  ticket_id: number;
  uploader_id: number;
  filename: string;
  content_type: string;
  size: number;
  created_at: string;
};

type AttachmentDownload = {
  url: string;
  expires_in: number;
};

const ALLOWED_EXTENSIONS =
  ".pdf, .png, .jpg, .jpeg, .gif, .webp, .txt, .doc, .docx (max 10 MB)";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatUploadedAt(iso: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

type AttachmentPanelProps = {
  ticketId: number;
};

export function AttachmentPanel({ ticketId }: AttachmentPanelProps) {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [downloadError, setDownloadError] = useState("");

  useEffect(() => {
    async function load() {
      setLoadError("");
      try {
        const data = await api<Attachment[]>(`/tickets/${ticketId}/attachments`);
        setAttachments(data);
      } catch (err) {
        setLoadError(
          err instanceof Error ? err.message : "Could not load attachments."
        );
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [ticketId]);

  async function handleUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selectedFile) {
      return;
    }

    setUploadError("");
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const created = await api<Attachment>(`/tickets/${ticketId}/attachments`, {
        method: "POST",
        body: formData,
      });

      setAttachments((prev) => [...prev, created]);
      setSelectedFile(null);
      const input = document.getElementById(
        `attachment-file-${ticketId}`
      ) as HTMLInputElement | null;
      if (input) {
        input.value = "";
      }
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Could not upload file."
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownload(attachment: Attachment) {
    setDownloadError("");
    setDownloadingId(attachment.id);
    try {
      const { url } = await api<AttachmentDownload>(
        `/tickets/${ticketId}/attachments/${attachment.id}/download`
      );
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setDownloadError(
        err instanceof Error ? err.message : "Could not start download."
      );
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <section
      className="space-y-4 rounded-lg border border-border bg-surface p-5"
      aria-labelledby={`attachments-heading-${ticketId}`}
    >
      <div>
        <h2
          id={`attachments-heading-${ticketId}`}
          className="text-sm font-semibold uppercase tracking-wide text-muted"
        >
          Attachments{attachments.length > 0 ? ` (${attachments.length})` : ""}
        </h2>
        <p className="mt-1 text-sm text-muted">
          Upload supporting files for this ticket. Allowed: {ALLOWED_EXTENSIONS}.
        </p>
      </div>

      <div className="rounded-lg border border-border">
        {isLoading && (
          <div className="flex items-center gap-2 p-4 text-sm text-muted">
            <Spinner size="h-4 w-4" />
            <span>Loading attachments…</span>
          </div>
        )}

        {!isLoading && loadError && (
          <p className="p-4 text-sm text-muted">{loadError}</p>
        )}

        {!isLoading && !loadError && attachments.length === 0 && (
          <p className="p-4 text-sm text-muted">No attachments yet.</p>
        )}

        {!isLoading && !loadError && attachments.length > 0 && (
          <ul className="divide-y divide-border">
            {attachments.map((attachment) => (
              <li
                key={attachment.id}
                className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {attachment.filename}
                  </p>
                  <p className="text-xs text-muted">
                    {formatFileSize(attachment.size)} · uploaded{" "}
                    {formatUploadedAt(attachment.created_at)}
                  </p>
                </div>
                <Button
                  type="button"
                  onClick={() => handleDownload(attachment)}
                  disabled={downloadingId === attachment.id}
                >
                  {downloadingId === attachment.id ? "Preparing…" : "Download"}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <form
        className="flex flex-col gap-3 sm:flex-row sm:items-end"
        onSubmit={handleUpload}
      >
        <div className="w-full sm:max-w-md">
          <label
            htmlFor={`attachment-file-${ticketId}`}
            className="mb-1 block text-sm font-medium"
          >
            Add file
          </label>
          <input
            id={`attachment-file-${ticketId}`}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.doc,.docx"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-muted file:mr-3 file:rounded-md file:border-0 file:bg-brand-light file:px-3 file:py-2 file:text-sm file:font-medium file:text-brand"
          />
        </div>
        <Button type="submit" disabled={isUploading || !selectedFile}>
          {isUploading ? "Uploading…" : "Upload"}
        </Button>
      </form>

      {uploadError && <p className="text-sm text-priority-urgent">{uploadError}</p>}
      {downloadError && (
        <p className="text-sm text-priority-urgent">{downloadError}</p>
      )}
    </section>
  );
}
