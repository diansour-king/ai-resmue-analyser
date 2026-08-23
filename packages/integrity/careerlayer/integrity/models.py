from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    INFO = "info"
    SUSPICIOUS = "suspicious"
    HIGH = "high"


class BBox(BaseModel):
    """A rectangle in PDF user space: origin top-left, y increasing downward.

    PyMuPDF already normalises MuPDF's coordinates to this convention, so these values can
    be handed to a page render of known DPI by multiplying by dpi/72.
    """

    model_config = ConfigDict(frozen=True)

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def intersection_area(self, other: "BBox") -> float:
        dx = min(self.x1, other.x1) - max(self.x0, other.x0)
        dy = min(self.y1, other.y1) - max(self.y0, other.y0)
        return dx * dy if dx > 0 and dy > 0 else 0.0

    def contained_fraction(self, other: "BBox") -> float:
        """How much of this box lies inside `other`, 0.0 to 1.0."""
        return self.intersection_area(other) / self.area if self.area > 0 else 0.0

    def union(self, other: "BBox") -> "BBox":
        return BBox(
            x0=min(self.x0, other.x0),
            y0=min(self.y0, other.y0),
            x1=max(self.x1, other.x1),
            y1=max(self.y1, other.y1),
        )


class TextSpan(BaseModel):
    """One run of characters sharing font, size, colour and render mode.

    The atomic unit of evidence. Every finding that points at document text points at one
    of these, and char_start/char_end index into the containing Page.text.
    """

    model_config = ConfigDict(frozen=True)

    page: int
    bbox: BBox
    text: str
    font: str
    font_size: float
    colour: tuple[float, float, float]
    render_mode: int
    opacity: float
    seqno: int
    char_start: int
    char_end: int
    char_boxes: tuple[tuple[float, float, float, float], ...] = ()
    """Per-character rectangles, parallel to `text`.

    Kept as plain tuples rather than BBox because there is one per character and the
    detectors that need them build a rectangle from a handful. Without these a finding
    about a single zero-width character would have to point at the whole span, which on a
    document written by a single text-writing pass is the whole page, and an overlay
    highlighting the whole page tells a reviewer nothing.
    """

    def box_over(self, start: int, end: int) -> BBox:
        """Tight rectangle around characters [start, end) of this span's text."""
        boxes = self.char_boxes[start:end]
        if not boxes:
            return self.bbox
        return BBox(
            x0=min(box[0] for box in boxes),
            y0=min(box[1] for box in boxes),
            x1=max(box[2] for box in boxes),
            y1=max(box[3] for box in boxes),
        )


class TextLine(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    bbox: BBox
    text: str


class OcrWord(BaseModel):
    """One word Tesseract read from the page raster, in PDF user space.

    Coordinates are converted back from raster pixels so that a finding raised against the
    rendered layer can be drawn on the same overlay as one raised against the text layer.
    """

    model_config = ConfigDict(frozen=True)

    page: int
    bbox: BBox
    text: str
    confidence: float


class Page(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: int
    cropbox: BBox
    rotation: int
    spans: tuple[TextSpan, ...]
    lines: tuple[TextLine, ...]
    ocr_words: tuple[OcrWord, ...]
    ocr_lines: tuple[str, ...] = ()
    image_rects: tuple[tuple[int, BBox], ...] = Field(
        default=(),
        description="Draw-order sequence number paired with the image's placement rectangle.",
    )

    @property
    def text(self) -> str:
        return "\n".join(span.text for span in self.spans)

    @property
    def ocr_text(self) -> str:
        return "\n".join(self.ocr_lines)


class ParsedDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    page_count: int
    pages: tuple[Page, ...]
    ocr_available: bool


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)

    detector_id: str
    detector_name: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    page: int
    bbox: BBox
    excerpt: str
    rationale: str
