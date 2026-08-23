import type { ProcessingState } from "@/lib/types";

const STEPS: { state: ProcessingState; label: string; detail: string }[] = [
  { state: "uploaded", label: "Received", detail: "Your PDF has been stored." },
  { state: "queued", label: "Queued", detail: "Waiting for an analysis worker." },
  {
    state: "processing",
    label: "Analysing",
    detail: "Extracting text, rendering pages at 200 DPI, and running the integrity checks.",
  },
  { state: "completed", label: "Done", detail: "Findings and evidence are ready." },
];

const FAILURE_TEXT: Record<string, string> = {
  invalid_pdf: "That file could not be read as a PDF.",
  extraction_failed: "The document could not be parsed.",
  render_failed: "The pages could not be rendered.",
  ocr_unavailable: "The text recognition service was unavailable.",
  storage_unavailable: "The document store was unavailable.",
  internal: "Something went wrong on our side.",
};

/**
 * Shows where the backend actually is, and nothing more.
 *
 * No percentage and no animated fill that implies progress the worker does not report.
 */
export function ProcessingStatus({
  state,
  failureCode,
}: {
  state: ProcessingState;
  failureCode: string | null;
}) {
  if (state === "failed") {
    return (
      <div
        role="alert"
        className="rounded-lg border border-error-container bg-error-container/40 p-6"
      >
        <p className="font-display text-headline-md text-on-error-container">
          This resume could not be analysed
        </p>
        <p className="mt-2 text-body-md text-on-surface-variant">
          {FAILURE_TEXT[failureCode ?? "internal"] ?? FAILURE_TEXT.internal}
        </p>
      </div>
    );
  }

  const currentIndex = STEPS.findIndex((step) => step.state === state);

  return (
    <div
      aria-live="polite"
      className="rounded-lg border border-surface-container-high bg-surface-container-lowest p-6 shadow-ocean"
    >
      <ol className="space-y-4">
        {STEPS.map((step, index) => {
          const done = index < currentIndex;
          const active = index === currentIndex;
          return (
            <li key={step.state} className="flex gap-4">
              <span
                aria-hidden
                className={`mt-1 h-3 w-3 shrink-0 rounded-full ${
                  done ? "bg-primary" : active ? "animate-pulse bg-primary" : "bg-surface-container-highest"
                }`}
              />
              <span>
                <span
                  className={`block text-body-md ${
                    active ? "font-semibold text-on-surface" : "text-on-surface-variant"
                  }`}
                >
                  {step.label}
                </span>
                {active ? (
                  <span className="block text-caption text-on-surface-variant">
                    {step.detail}
                  </span>
                ) : null}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
