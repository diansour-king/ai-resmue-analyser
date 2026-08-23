import Link from "next/link";

import type { Severity } from "@/lib/types";

const ORDER: Severity[] = ["high", "suspicious", "info"];

const TONE: Record<Severity, string> = {
  high: "border-error/40 bg-error-container/40 text-on-error-container",
  suspicious: "border-[#e0a341]/50 bg-[#ffe9c7] text-[#6b4400]",
  info: "border-secondary-container bg-secondary-container/50 text-on-secondary-container",
};

const LABEL: Record<Severity, string> = {
  high: "High",
  suspicious: "Suspicious",
  info: "Info",
};

/**
 * Three counts, not one risk score.
 *
 * Every number here is a row count from the findings table, and every tile leads to the
 * findings behind it. A single blended score would be exactly the opaque number this product
 * refuses to produce.
 */
export function IntegritySummary({
  counts,
  evidenceHref,
}: {
  counts: Record<Severity, number>;
  evidenceHref: string;
}) {
  const total = ORDER.reduce((sum, severity) => sum + counts[severity], 0);

  return (
    <section aria-labelledby="integrity-heading">
      <h2 id="integrity-heading" className="font-display text-headline-md text-on-surface">
        Integrity findings
      </h2>
      {total === 0 ? (
        <p className="mt-3 rounded-lg border border-surface-container-high bg-surface-container-lowest p-6 text-body-md text-on-surface-variant">
          Nothing flagged. The text layer and the rendered pages agree.
        </p>
      ) : (
        <div className="mt-3 grid grid-cols-3 gap-3">
          {ORDER.map((severity) => (
            <Link
              key={severity}
              href={`${evidenceHref}?severity=${severity}`}
              className={`rounded-lg border p-5 transition-transform hover:-translate-y-0.5 ${TONE[severity]}`}
            >
              <span className="block font-display text-display leading-none">
                {counts[severity]}
              </span>
              <span className="mt-2 block text-label-md">{LABEL[severity]}</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
