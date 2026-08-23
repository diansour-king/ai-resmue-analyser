import pymupdf

from .models import BBox, TextLine, TextSpan

_MAX_EXCERPT = 400


def _to_bbox(rect: tuple[float, float, float, float] | pymupdf.Rect) -> BBox:
    if isinstance(rect, pymupdf.Rect):
        return BBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1)
    return BBox(x0=rect[0], y0=rect[1], x1=rect[2], y1=rect[3])


def _span_text(chars: list[tuple[int, int, tuple[float, float], tuple[float, ...]]]) -> str:
    return "".join(chr(char[0]) for char in chars)


def extract_spans(page: pymupdf.Page, page_number: int) -> tuple[TextSpan, ...]:
    """Read spans with the attributes the integrity detectors depend on.

    get_texttrace is used rather than get_text("dict") because only the former reports the
    text render mode, the fill opacity and the draw-order sequence number. Those three are
    exactly what separates a hidden-text injection from ordinary body copy, and get_text
    discards all of them.
    """
    spans: list[TextSpan] = []
    offset = 0
    for raw in page.get_texttrace():
        text = _span_text(raw["chars"])
        if not text:
            continue
        colour = raw["color"]
        spans.append(
            TextSpan(
                page=page_number,
                bbox=_to_bbox(raw["bbox"]),
                text=text,
                font=raw["font"],
                font_size=raw["size"],
                colour=_as_rgb(colour, raw["colorspace"]),
                render_mode=raw["type"],
                opacity=raw["opacity"],
                seqno=raw["seqno"],
                char_start=offset,
                char_end=offset + len(text),
                char_boxes=tuple(tuple(char[3]) for char in raw["chars"]),
            )
        )
        # +1 for the newline that Page.text joins spans with, so offsets stay valid there.
        offset += len(text) + 1
    return tuple(spans)


def _as_rgb(colour: tuple[float, ...], colorspace: int) -> tuple[float, float, float]:
    """Normalise a fill colour to RGB in 0..1.

    MuPDF reports the colour in the span's own colourspace: 1 component for greyscale, 3
    for RGB, 4 for CMYK. Contrast comparison needs one space, and converting here keeps
    that conversion out of the detector.
    """
    if colorspace == 1 and len(colour) >= 1:
        grey = colour[0]
        return (grey, grey, grey)
    if colorspace == 4 and len(colour) >= 4:
        cyan, magenta, yellow, black = colour[:4]
        return (
            (1.0 - cyan) * (1.0 - black),
            (1.0 - magenta) * (1.0 - black),
            (1.0 - yellow) * (1.0 - black),
        )
    if len(colour) >= 3:
        return (colour[0], colour[1], colour[2])
    return (0.0, 0.0, 0.0)


def extract_lines(page: pymupdf.Page, page_number: int) -> tuple[TextLine, ...]:
    """Line segmentation for the extraction-delta comparison.

    MuPDF's own segmentation is used instead of grouping spans by y-coordinate because it
    already handles multi-column layouts and rotated text, which resumes built from Word
    and LaTeX templates both produce.
    """
    lines: list[TextLine] = []
    page_dict = page.get_text("dict")
    for block in page_dict["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                lines.append(TextLine(page=page_number, bbox=_to_bbox(line["bbox"]), text=text))
    return tuple(lines)


def extract_image_rects(page: pymupdf.Page) -> tuple[tuple[int, BBox], ...]:
    """Image placements paired with their position in the page's draw order.

    get_bboxlog entries are indexed by the same sequence numbers get_texttrace reports, so
    comparing the two tells us whether an image was painted after a span, which is the
    difference between an occluded span and one that merely overlaps a background picture.
    """
    rects: list[tuple[int, BBox]] = []
    for seqno, (kind, rect) in enumerate(page.get_bboxlog()):
        if "image" in kind:
            rects.append((seqno, _to_bbox(rect)))
    return tuple(rects)


def excerpt(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= _MAX_EXCERPT:
        return collapsed
    return collapsed[: _MAX_EXCERPT - 1] + "…"
