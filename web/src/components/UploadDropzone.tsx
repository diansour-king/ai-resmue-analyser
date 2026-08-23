"use client";

import { useCallback, useRef, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { UploadAccepted } from "@/lib/types";

type Phase = "idle" | "invalid" | "uploading" | "done" | "failed";

const MAX_BYTES = 20 * 1024 * 1024;

export function UploadDropzone({ onUploaded }: { onUploaded: (r: UploadAccepted) => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [dragging, setDragging] = useState(false);

  const start = useCallback(
    async (file: File) => {
      // Checked here so an obvious mistake costs nothing, and checked again on the server by
      // parsing the file, because a client-side check is a courtesy and not a control.
      if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
        setPhase("invalid");
        setMessage("CareerLayer reads PDFs. Export your resume as a PDF and try again.");
        return;
      }
      if (file.size > MAX_BYTES) {
        setPhase("invalid");
        setMessage("That file is over 20MB.");
        return;
      }

      setPhase("uploading");
      setMessage(null);
      setProgress(0);
      try {
        const accepted = await api.upload(file, setProgress);
        setPhase("done");
        onUploaded(accepted);
      } catch (error) {
        setPhase("failed");
        setMessage(
          error instanceof ApiError ? error.message : "The upload failed. Try again.",
        );
      }
    },
    [onUploaded],
  );

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a resume PDF"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files[0];
          if (file) void start(file);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-center transition-colors ${
          dragging
            ? "border-primary bg-primary-fixed/30"
            : "border-outline-variant bg-surface-container-lowest hover:border-primary/60"
        }`}
      >
        <p className="font-display text-headline-md text-on-surface">Drop your resume here</p>
        <p className="mt-2 text-body-md text-on-surface-variant">
          or click to choose a file. PDF, up to 20MB and 40 pages.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          data-testid="file-input"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void start(file);
          }}
        />
      </div>

      {phase === "uploading" ? (
        <div className="mt-6" aria-live="polite">
          <div className="flex justify-between text-label-md text-on-surface-variant">
            <span>Uploading</span>
            <span>{Math.round(progress * 100)}%</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-container">
            <div
              role="progressbar"
              aria-valuenow={Math.round(progress * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              className="h-full rounded-full bg-primary transition-[width]"
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
          <p className="mt-2 text-caption text-on-surface-variant">
            This bar is the transfer only. Analysis starts once the file arrives.
          </p>
        </div>
      ) : null}

      {message ? (
        <p role="alert" className="mt-6 rounded-lg bg-error-container/50 p-4 text-body-md text-on-error-container">
          {message}
        </p>
      ) : null}
    </div>
  );
}
