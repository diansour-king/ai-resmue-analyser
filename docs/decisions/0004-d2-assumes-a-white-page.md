# 0004. Low-contrast detection assumes a white page

Status: accepted
Date: 2026-08-22

## Context

D2 flags text whose fill colour is too close to what sits behind it to be read. "What sits
behind it" is the hard part: the background behind a span could be the page, a coloured
banner, a table cell fill, or a photograph.

## Options considered

**Sample the background from a page render.** Rasterise the page and take the modal colour
inside the span's rectangle, which for any realistic amount of text is the background rather
than the glyphs. Correct in every case, including white text on a dark header. Costs a raster
per page even when the caller asked for text-layer detectors only, which is the mode the
API's fast path will use.

**Read the page's drawing operations and find the last fill covering the span.** Exact and
cheap, but has to reimplement enough of the PDF imaging model to handle transparency groups,
clipping paths and blend modes correctly. That is a large amount of code to get subtly wrong.

**Assume white.** Chosen for now.

## Decision

Contrast is computed against white, using the WCAG relative-luminance ratio, with the span's
fill opacity blended toward the background first so that a near-white opaque glyph and a
black glyph at 2% opacity produce the same number.

The floor is 1.6:1, which is far below the 4.5:1 an accessibility audit would use. The goal
is text that is effectively invisible, not text that is hard to read: flagging grey-on-white
footnotes would be a false positive on a large fraction of real resumes.

## Consequences

**The known miss: light text on a dark background is not detected.** A resume with a dark
banner and white text inside it will be read as high contrast when it is high contrast, which
is correct — but an injection written in near-black text on that same dark banner will be
missed entirely. This is a real gap, not a theoretical one, and it is the first thing to fix
if the corpus in phase 4 contains templates with dark sections.

D6 is the partial backstop: text invisible against its background is text OCR will not read,
so the extraction delta should catch it even when D2 cannot explain why. That is a reason to
keep the floor here conservative rather than to treat the gap as covered.

Spans in render mode 3 are skipped, because D1 owns them and one cause should produce one
finding rather than two with different explanations.
