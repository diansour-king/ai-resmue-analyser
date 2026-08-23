import type { Severity } from "@/lib/types";

const STYLES: Record<Severity, string> = {
  high: "bg-error-container text-on-error-container",
  suspicious: "bg-[#ffe1b3] text-[#6b4400]",
  info: "bg-secondary-container text-on-secondary-container",
};

const LABELS: Record<Severity, string> = {
  high: "High",
  suspicious: "Suspicious",
  info: "Info",
};

export function SeverityChip({ severity }: { severity: Severity }) {
  return (
    <span className={`rounded-full px-2.5 py-1 text-caption font-semibold ${STYLES[severity]}`}>
      {LABELS[severity]}
    </span>
  );
}

export const SEVERITY_LABELS = LABELS;
