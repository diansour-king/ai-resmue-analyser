import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

import pymupdf

from .models.resume import FailureCode

ZERO_WIDTH = frozenset(
    {
        "\u200b",  # zero width space
        "\u200c",  # zero width non-joiner
        "\u200d",  # zero width joiner
        "\u2060",  # word joiner
        "\ufeff",  # zero width no-break space
        "\u00ad",  # soft hyphen
    }
)

BIDI_CONTROLS = frozenset(
    {
        "\u202a",  # left-to-right embedding
        "\u202b",  # right-to-left embedding
        "\u202c",  # pop directional formatting
        "\u202d",  # left-to-right override
        "\u202e",  # right-to-left override
        "\u2066",  # left-to-right isolate
        "\u2067",  # right-to-left isolate
        "\u2068",  # first strong isolate
        "\u2069",  # pop directional isolate
    }
)

MAX_JD_TOKENS = 8000


class RejectedJob(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class BoilerplateSpan:
    start: int
    end: int
    category: str


@dataclass(frozen=True)
class NormalizedJobDescription:
    normalized_text: str
    sha256: str
    zero_width_count: int
    bidi_count: int
    token_count: int
    boilerplate_spans: list[BoilerplateSpan] = field(default_factory=list)


@dataclass(frozen=True)
class AcceptedJobUpload:
    sha256: str
    byte_size: int
    page_count: int


_BOILERPLATE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "equal_opportunity",
        re.compile(
            r"(?:we\s+are\s+an?\s+)?equal\s+opportunity\s+employer[^\n]*(?:\n[^\n]+)*|"
            r"affirmative\s+action\s+employer[^\n]*(?:\n[^\n]+)*|"
            r"(?:does\s+not|do\s+not)\s+discriminate\s+(?:on\s+the\s+basis|based\s+on)[^\n]*(?:\n[^\n]+)*",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        "benefits",
        re.compile(
            r"(?:^|\n)\s*(?:benefits|what\s+we\s+offer|perks\s*(?:&|and)\s*benefits|compensation\s*(?:&|and)\s*benefits)\s*:\s*(?:\n\s*[-*•\d\.]+[^\n]+)+",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        "application_instructions",
        re.compile(
            r"(?:how\s+to\s+apply|to\s+apply\s*,?\s*please\s+(?:submit|send|visit)|click\s+apply\s+now|send\s+(?:your\s+)?resume\s+to)\s*:\s*[^\n]*(?:\n[^\n]+)*",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
]


def estimate_tokens(text: str) -> int:
    """Fast, deterministic token estimation for prompt safety limits.

    1 token is approximately 4 characters or ~0.75 words. We take the max of character-based
    and word-based estimates so whitespace-sparse or token-dense content is safely bounded.
    """
    if not text:
        return 0
    char_estimate = (len(text) + 3) // 4
    word_estimate = len(text.split())
    return max(char_estimate, word_estimate)


def normalize_job_text(raw_text: str) -> NormalizedJobDescription:
    """Deterministic normalization for job descriptions (Phase 3 architecture section 4.2).

    1. Decode and reject invalid UTF-8.
    2. Unicode NFKC normalization.
    3. Strip zero-width and bidi control characters, recording their presence.
    4. Normalize line endings to \\n; collapse runs of 3+ blank lines to 2.
    5. Mark boilerplate spans by heuristic without modifying offsets.
    6. Compute sha256 of normalized_text for deduplication.
    """
    if not raw_text or not raw_text.strip():
        raise RejectedJob("invalid_input", "Job description text cannot be empty.")

    # 1 & 2. NFKC normalization
    text = unicodedata.normalize("NFKC", raw_text)

    # 3. Strip zero-width and bidi control characters, recording count
    zero_width_count = sum(1 for char in text if char in ZERO_WIDTH)
    bidi_count = sum(1 for char in text if char in BIDI_CONTROLS)

    cleaned_chars = [char for char in text if char not in ZERO_WIDTH and char not in BIDI_CONTROLS]
    text = "".join(cleaned_chars)

    # 4. Line ending normalization
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse 3+ consecutive newlines to 2 (e.g. \n\n\n+ -> \n\n)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if not text:
        raise RejectedJob("invalid_input", "Job description text cannot be empty.")

    token_count = estimate_tokens(text)
    if token_count > MAX_JD_TOKENS:
        raise RejectedJob(
            "token_limit_exceeded",
            f"Job descriptions must be {MAX_JD_TOKENS} tokens or fewer (received ~{token_count}).",
        )

    # 5. Mark boilerplate spans
    boilerplate_spans: list[BoilerplateSpan] = []
    for category, pattern in _BOILERPLATE_PATTERNS:
        for match in pattern.finditer(text):
            boilerplate_spans.append(
                BoilerplateSpan(start=match.start(), end=match.end(), category=category)
            )

    # 6. Compute sha256
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

    return NormalizedJobDescription(
        normalized_text=text,
        sha256=sha256,
        zero_width_count=zero_width_count,
        bidi_count=bidi_count,
        token_count=token_count,
        boilerplate_spans=boilerplate_spans,
    )


def accept_pdf(content: bytes, *, max_bytes: int, max_pages: int) -> AcceptedJobUpload:
    """Validate an uploaded PDF job description before storage or parsing."""
    if not content:
        raise RejectedJob("invalid_pdf", "That file is empty.")
    if len(content) > max_bytes:
        raise RejectedJob(
            "file_too_large",
            f"Job description files must be under {max_bytes // (1024 * 1024)}MB.",
        )

    try:
        document = pymupdf.open(stream=content, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise RejectedJob("invalid_pdf", "That file is not a readable PDF.") from exc

    try:
        if document.needs_pass:
            raise RejectedJob(
                "invalid_pdf",
                "That PDF is password protected, so it cannot be analysed.",
            )
        page_count = document.page_count
    finally:
        document.close()

    if page_count < 1:
        raise RejectedJob("invalid_pdf", "That PDF has no pages.")
    if page_count > max_pages:
        raise RejectedJob(
            "page_limit_exceeded",
            f"Job descriptions must be {max_pages} pages or fewer.",
        )

    return AcceptedJobUpload(
        sha256=hashlib.sha256(content).hexdigest(),
        byte_size=len(content),
        page_count=page_count,
    )


def failure_for_job(code: str) -> FailureCode:
    if code == "invalid_pdf":
        return FailureCode.INVALID_PDF
    return FailureCode.INTERNAL
