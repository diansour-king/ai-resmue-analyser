# 0003. Tesseract as the rendered-layer reader, and 200 DPI as the render resolution

Status: accepted
Date: 2026-08-22

## Context

The rendered layer is the half of the dual extraction that stands in for a human eye. Its
accuracy sets the false positive rate of D6 directly: every word OCR fails to read is a word
the text layer appears to have invented.

The build specification names `pytesseract` plus `tesseract-ocr`, and says to evaluate
PaddleOCR if accuracy on two-column layouts turns out to be poor.

## Options considered

**Tesseract.** Mature, packaged everywhere, no model download at install time, and its
`image_to_data` output carries word-level bounding boxes plus its own block, paragraph and
line numbering. That numbering is what the line grouping in D6 is built on.

**PaddleOCR.** Better reported accuracy on dense and multi-column layouts, at the cost of a
heavyweight dependency, a model download, and a substantially larger container image for the
worker.

## Decision

Tesseract, for now. PaddleOCR is not evaluated in phase 1 because the trigger condition in
the specification has not been reached: there is no two-column fixture and no real corpus to
measure against, so a comparison run today would compare two engines on documents that both
read perfectly and would prove nothing.

**The comparison is deferred to phase 4, with an explicit trigger.** Once the corpus exists,
if the per-line alignment scores from `alignment_scores` on clean two-column resumes fall
below the D6 floor often enough to require dropping that floor beneath roughly 60, the engine
is the problem rather than the threshold, and PaddleOCR gets measured against the same corpus
with the result recorded as a superseding ADR.

Render resolution is 200 DPI. Below it Tesseract's word error rate on 8pt body text climbs
fast enough to manufacture D6 findings on clean documents; above it the raster and the OCR
pass both get more expensive with no measured gain on resume-sized type.

## Consequences

- The worker and any developer machine need the `tesseract-ocr` system package. It is not a
  Python dependency and `pip install` will not provide it.
- `OcrUnavailable` is a distinct exception type from `ExtractionFailed` precisely because
  this is an environment problem, not a document problem: the same PDF succeeds once the
  binary is installed.
- Without OCR, D6 declines to run rather than reporting every line as missing. The CLI says
  so in its output, because a run with five of six detectors silently looks the same as a
  clean document.
- Committing to Tesseract's block and line numbering for D6's line grouping means switching
  engines later also means rewriting that grouping. That is a real cost and it is the main
  argument for deciding sooner rather than later.
