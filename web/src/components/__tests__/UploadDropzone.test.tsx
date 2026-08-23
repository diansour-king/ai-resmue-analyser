import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UploadDropzone } from "../UploadDropzone";
import { ApiError, api } from "@/lib/api";

afterEach(() => vi.restoreAllMocks());

function pdf(name = "resume.pdf", size = 1024) {
  const file = new File(["%PDF-1.7"], name, { type: "application/pdf" });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

describe("UploadDropzone", () => {
  it("uploads a PDF and reports the accepted resume", async () => {
    const accepted = {
      resume_id: "r-1",
      state: "queued" as const,
      filename: "resume.pdf",
      page_count: 1,
      duplicate_of_existing: false,
    };
    vi.spyOn(api, "upload").mockResolvedValue(accepted);
    const onUploaded = vi.fn();

    render(<UploadDropzone onUploaded={onUploaded} />);
    await userEvent.upload(screen.getByTestId("file-input"), pdf());

    expect(onUploaded).toHaveBeenCalledWith(accepted);
  });

  it("refuses a dropped file that is not a PDF without contacting the server", async () => {
    // The drop path, not the picker: a file input honours its accept attribute, and drag and
    // drop does not. This is the route by which a .docx actually reaches the handler.
    const upload = vi.spyOn(api, "upload");

    render(<UploadDropzone onUploaded={vi.fn()} />);
    fireEvent.drop(screen.getByRole("button", { name: /upload a resume pdf/i }), {
      dataTransfer: { files: [new File(["hello"], "resume.docx", { type: "text/plain" })] },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(/PDF/i);
    expect(upload).not.toHaveBeenCalled();
  });

  it("accepts a dropped PDF", async () => {
    const accepted = {
      resume_id: "r-2",
      state: "queued" as const,
      filename: "resume.pdf",
      page_count: 2,
      duplicate_of_existing: false,
    };
    vi.spyOn(api, "upload").mockResolvedValue(accepted);
    const onUploaded = vi.fn();

    render(<UploadDropzone onUploaded={onUploaded} />);
    fireEvent.drop(screen.getByRole("button", { name: /upload a resume pdf/i }), {
      dataTransfer: { files: [pdf()] },
    });

    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(accepted));
  });

  it("refuses a file over the size cap", async () => {
    render(<UploadDropzone onUploaded={vi.fn()} />);

    await userEvent.upload(screen.getByTestId("file-input"), pdf("big.pdf", 21 * 1024 * 1024));

    expect(await screen.findByRole("alert")).toHaveTextContent(/20MB/);
  });

  it("shows the server's own message when the upload is rejected", async () => {
    vi.spyOn(api, "upload").mockRejectedValue(
      new ApiError(422, "page_limit_exceeded", "Resumes must be 40 pages or fewer.", "req-1"),
    );

    render(<UploadDropzone onUploaded={vi.fn()} />);
    await userEvent.upload(screen.getByTestId("file-input"), pdf());

    expect(await screen.findByRole("alert")).toHaveTextContent(/40 pages or fewer/);
  });
});
