class IntegrityError(Exception):
    """Base for every failure this package raises deliberately."""


class ExtractionFailed(IntegrityError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"could not extract {path}: {reason}")
        self.path = path
        self.reason = reason


class OcrUnavailable(IntegrityError):
    """The Tesseract binary is missing or unusable.

    Distinct from ExtractionFailed because it is an environment problem, not a document
    problem: the same PDF will succeed once the binary is installed, and the caller may
    reasonably choose to run the text-layer detectors anyway.
    """


class RenderFailed(IntegrityError):
    def __init__(self, page: int, reason: str) -> None:
        super().__init__(f"could not rasterise page {page}: {reason}")
        self.page = page
        self.reason = reason
