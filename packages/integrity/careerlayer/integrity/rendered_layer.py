import shutil
from typing import Any, NamedTuple

import pymupdf
import pytesseract
from PIL import Image

from .errors import OcrUnavailable, RenderFailed
from .models import BBox, OcrWord

RENDER_DPI = 200

_POINTS_PER_INCH = 72.0
_MIN_WORD_CONFIDENCE = 30.0


class OcrResult(NamedTuple):
    words: tuple[OcrWord, ...]
    lines: tuple[str, ...]


def ocr_is_available() -> bool:
    return shutil.which("tesseract") is not None


def render_page(page: pymupdf.Page, dpi: int = RENDER_DPI) -> Image.Image:
    """Rasterise one page at the DPI the OCR pass is tuned for.

    200 DPI is the floor at which Tesseract reads 8pt body text reliably. Below it the word
    error rate climbs fast enough to manufacture extraction-delta findings on clean
    documents, and a false flag is this system's expensive error.
    """
    try:
        pixmap = page.get_pixmap(dpi=dpi)
    except (RuntimeError, ValueError) as exc:
        raise RenderFailed(page.number + 1, str(exc)) from exc
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def read_page(image: Image.Image, page_number: int, dpi: int = RENDER_DPI) -> OcrResult:
    """Run one OCR pass and return both words and lines from it.

    One pass rather than two: OCR dominates the wall-clock cost of analysing a document, and
    words and lines are two views of the same Tesseract output. Line grouping uses
    Tesseract's own block and line numbering rather than reconstructing lines from word
    coordinates, which would duplicate work already done and disagree with it on
    hyphenation and column breaks.

    Word coordinates are converted out of pixel space into PDF user space so a finding
    raised against what a human sees can be drawn on the same overlay as one raised against
    what the machine reads.
    """
    if not ocr_is_available():
        raise OcrUnavailable("the tesseract binary is not on PATH")
    try:
        data: dict[str, list[Any]] = pytesseract.image_to_data(
            image, output_type=pytesseract.Output.DICT
        )
    except pytesseract.TesseractError as exc:
        raise OcrUnavailable(f"tesseract failed: {exc}") from exc
    except OSError as exc:
        raise OcrUnavailable(f"could not invoke tesseract: {exc}") from exc

    scale = _POINTS_PER_INCH / dpi
    words: list[OcrWord] = []
    grouped: dict[tuple[int, int, int], list[str]] = {}

    for index, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
        if not text or float(data["conf"][index]) < _MIN_WORD_CONFIDENCE:
            continue
        left, top = data["left"][index], data["top"][index]
        width, height = data["width"][index], data["height"][index]
        words.append(
            OcrWord(
                page=page_number,
                bbox=BBox(
                    x0=left * scale,
                    y0=top * scale,
                    x1=(left + width) * scale,
                    y1=(top + height) * scale,
                ),
                text=text,
                confidence=float(data["conf"][index]) / 100.0,
            )
        )
        key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
        grouped.setdefault(key, []).append(text)

    lines = tuple(" ".join(line_words) for _, line_words in sorted(grouped.items()))
    return OcrResult(words=tuple(words), lines=lines)
