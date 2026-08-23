from pathlib import Path

import pymupdf

from .errors import ExtractionFailed, OcrUnavailable
from .models import BBox, OcrWord, Page, ParsedDocument
from .rendered_layer import RENDER_DPI, ocr_is_available, read_page, render_page
from .text_layer import extract_image_rects, extract_lines, extract_spans


def parse(path: Path, *, with_ocr: bool = True, dpi: int = RENDER_DPI) -> ParsedDocument:
    """Read a PDF twice: once as the machine reads it, once as a human sees it.

    The difference between the two reads is the engine's central primitive, so both halves
    are produced here and no detector re-opens the file.

    with_ocr=False yields a document whose ocr_words and ocr lines are empty. The
    text-layer detectors still work; D6 declines to run rather than reporting every line as
    missing.
    """
    try:
        document = pymupdf.open(path)
    except (pymupdf.FileDataError, RuntimeError) as exc:
        raise ExtractionFailed(str(path), str(exc)) from exc

    run_ocr = with_ocr and ocr_is_available()
    pages: list[Page] = []
    try:
        for index in range(document.page_count):
            pages.append(_parse_page(document[index], index + 1, run_ocr=run_ocr, dpi=dpi))
    finally:
        document.close()

    return ParsedDocument(
        path=str(path),
        page_count=len(pages),
        pages=tuple(pages),
        ocr_available=run_ocr,
    )


def _parse_page(page: pymupdf.Page, number: int, *, run_ocr: bool, dpi: int) -> Page:
    ocr_words: tuple[OcrWord, ...] = ()
    ocr_line_texts: tuple[str, ...] = ()
    if run_ocr:
        try:
            result = read_page(render_page(page, dpi=dpi), number, dpi=dpi)
        except OcrUnavailable:
            # Tesseract can disappear between the availability probe and the call, for
            # example inside a container whose filesystem is being swapped under it. One
            # unreadable page must not lose the text-layer findings for the whole document.
            ocr_words, ocr_line_texts = (), ()
        else:
            ocr_words, ocr_line_texts = result.words, result.lines

    cropbox = page.cropbox
    return Page(
        number=number,
        cropbox=BBox(x0=cropbox.x0, y0=cropbox.y0, x1=cropbox.x1, y1=cropbox.y1),
        rotation=page.rotation,
        spans=extract_spans(page, number),
        lines=extract_lines(page, number),
        ocr_words=ocr_words,
        image_rects=extract_image_rects(page),
        ocr_lines=ocr_line_texts,
    )
