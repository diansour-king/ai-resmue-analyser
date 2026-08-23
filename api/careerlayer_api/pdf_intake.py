import hashlib
from dataclasses import dataclass

import pymupdf

from .models.resume import FailureCode


class RejectedUpload(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AcceptedUpload:
    sha256: str
    byte_size: int
    page_count: int


def accept(content: bytes, *, max_bytes: int, max_pages: int) -> AcceptedUpload:
    """Decide whether these bytes are a PDF this system will take, before storing anything.

    The file is validated by parsing it, never by its extension or the Content-Type the
    client claimed. Both are attacker-controlled strings, and the whole premise here is that
    the uploader is not trusted.

    Page count is read now rather than in the worker so that a 900-page document is refused
    at the door instead of after it has been stored and queued.
    """
    if not content:
        raise RejectedUpload("invalid_pdf", "That file is empty.")
    if len(content) > max_bytes:
        raise RejectedUpload(
            "file_too_large", f"Resumes must be under {max_bytes // (1024 * 1024)}MB."
        )

    try:
        document = pymupdf.open(stream=content, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise RejectedUpload("invalid_pdf", "That file is not a readable PDF.") from exc

    try:
        if document.needs_pass:
            raise RejectedUpload(
                "invalid_pdf", "That PDF is password protected, so it cannot be analysed."
            )
        page_count = document.page_count
    finally:
        document.close()

    if page_count < 1:
        raise RejectedUpload("invalid_pdf", "That PDF has no pages.")
    if page_count > max_pages:
        raise RejectedUpload("page_limit_exceeded", f"Resumes must be {max_pages} pages or fewer.")

    return AcceptedUpload(
        sha256=hashlib.sha256(content).hexdigest(),
        byte_size=len(content),
        page_count=page_count,
    )


def failure_for(code: str) -> FailureCode:
    return FailureCode.INVALID_PDF if code == "invalid_pdf" else FailureCode.INTERNAL
