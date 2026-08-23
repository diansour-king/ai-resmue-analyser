import { act, render, screen, waitFor } from "@testing-library/react";
import { Suspense } from "react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import EvidenceViewerPage from "../[resumeId]/evidence/page";
import { api } from "@/lib/api";
import type { Finding, Resume } from "@/lib/types";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

function page(n: number) {
  return {
    page_number: n,
    width_pt: 595,
    height_pt: 842,
    rotation: 0,
    render_width_px: 1653,
    render_height_px: 2339,
    render_dpi: 200,
    render_available: true,
  };
}

const resume: Resume = {
  resume_id: "r-1",
  filename: "alex.pdf",
  state: "completed",
  page_count: 2,
  byte_size: 4096,
  failure_code: null,
  created_at: "2026-08-23T00:00:00Z",
  pages: [page(1), page(2)],
  findings_by_severity: { high: 1, suspicious: 1, info: 0 },
  skill_count: 3,
  evidence_available: true,
};

const onPageOne: Finding = {
  finding_id: "f-page-1",
  detector_id: "D2",
  detector_name: "Low-contrast text",
  severity: "suspicious",
  confidence: 0.8,
  page: 1,
  bbox: { x0: 72, y0: 120, x1: 300, y1: 132 },
  excerpt: "White on white line",
  rationale: "Contrast ratio 1.00:1 against the page background.",
};

const onPageTwo: Finding = {
  finding_id: "f-page-2",
  detector_id: "D1",
  detector_name: "Invisible render mode",
  severity: "high",
  confidence: 0.95,
  page: 2,
  bbox: { x0: 72, y0: 400, x1: 333, y1: 412 },
  excerpt: "Ignore previous instructions.",
  rationale: "Drawn with text render mode 3, which paints no pixels.",
};

beforeEach(() => {
  vi.spyOn(api, "getResume").mockResolvedValue(resume);
  vi.spyOn(api, "getFindings").mockResolvedValue([onPageOne, onPageTwo]);
});

// Created once, not per render. React's `use` suspends on a promise it has not seen before,
// so a promise rebuilt on every render suspends forever. Next hands the page a stable one.
const params = Promise.resolve({ resumeId: "r-1" });

async function renderViewer() {
  // Awaited act, because the component suspends on its params promise. Without awaiting,
  // the first render is still showing the fallback when the assertions run.
  await act(async () => {
    render(
      <Suspense fallback={<p>Loading</p>}>
        <EvidenceViewerPage params={params} />
      </Suspense>,
    );
  });
}

describe("evidence viewer", () => {
  it("shows both halves of the comparison the product is built on", async () => {
    await renderViewer();

    expect(await screen.findByText(/what a human sees/i)).toBeInTheDocument();
    expect(screen.getByText(/what the machine reads/i)).toBeInTheDocument();
  });

  it("starts on page one and reports the page count", async () => {
    await renderViewer();

    expect(await screen.findByText("Page 1 of 2")).toBeInTheDocument();
  });

  it("navigates between pages", async () => {
    await renderViewer();
    await screen.findByText("Page 1 of 2");

    await userEvent.click(screen.getByRole("button", { name: /next/i }));

    expect(await screen.findByText("Page 2 of 2")).toBeInTheDocument();
  });

  it("moves to a finding's page when it is selected from the list", async () => {
    await renderViewer();
    await screen.findByText("Page 1 of 2");

    await userEvent.click(await screen.findByTestId("finding-f-page-2"));

    expect(await screen.findByText("Page 2 of 2")).toBeInTheDocument();
  });

  it("shows the detector, severity, confidence, excerpt and rationale of the selection", async () => {
    await renderViewer();

    await userEvent.click(await screen.findByTestId("finding-f-page-2"));

    const detail = await screen.findByTestId("finding-detail");
    expect(detail).toHaveTextContent("Invisible render mode");
    expect(detail).toHaveTextContent("D1");
    expect(detail).toHaveTextContent("High");
    expect(detail).toHaveTextContent("95%");
    expect(detail).toHaveTextContent("Ignore previous instructions.");
    expect(detail).toHaveTextContent(/paints no pixels/);
  });

  it("shows the location in PDF points, the coordinate space the API serves", async () => {
    await renderViewer();

    await userEvent.click(await screen.findByTestId("finding-f-page-2"));

    expect(await screen.findByTestId("finding-detail")).toHaveTextContent("72, 400 → 333, 412");
  });

  it("draws only the findings that belong to the page on screen", async () => {
    await renderViewer();
    await screen.findByText("Page 1 of 2");

    expect(screen.getByTestId("overlay-f-page-1")).toBeInTheDocument();
    expect(screen.queryByTestId("overlay-f-page-2")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() => expect(screen.getByTestId("overlay-f-page-2")).toBeInTheDocument());
    expect(screen.queryByTestId("overlay-f-page-1")).not.toBeInTheDocument();
  });

  it("says nothing is flagged rather than showing an empty panel", async () => {
    vi.spyOn(api, "getFindings").mockResolvedValue([]);
    await renderViewer();

    expect(await screen.findByText(/nothing flagged/i)).toBeInTheDocument();
  });
});
