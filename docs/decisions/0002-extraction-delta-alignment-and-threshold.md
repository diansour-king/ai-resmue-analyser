# 0002. How the extraction delta aligns text, and where its threshold sits

Status: accepted
Date: 2026-08-22

## Context

D6 compares what the PDF text layer contains against what OCR reads from the rendered page.
It is the detector that catches attacks nobody has named yet, because any technique that
makes text unreadable to a human while leaving it in the text layer produces a gap here.

It is also the detector that will generate the false positives if it is wrong. OCR is noisy
on text that is genuinely present: it drops characters, merges words, misreads ligatures,
and breaks a wrapped line in two as readily as it runs two lines together. A naive set
difference between the two reads flags most of every clean resume.

A false flag costs a person a job. A missed injection costs a company one wasted interview.
Every choice below is tuned in that direction.

## Options considered

**Exact set difference on tokens.** Rejected without measuring. It flags any line containing
a word Tesseract misread, which on real documents is most pages.

**Whole-page similarity.** Comparing the concatenated text layer against the concatenated OCR
text produces one number per page. Rejected: it detects that something is wrong but cannot
say which line, and a finding with no location cannot be drawn on a page render, which is
what the phase 2 viewer needs.

**Token-level alignment only.** Rejected. Token alignment loses word order entirely, so a
line whose words all appear elsewhere on the page scores as present when it is not.

**Line alignment, then token alignment as a fallback.** Chosen.

## Decision

Normalise both sides first, because case, whitespace, punctuation and Unicode form are all
things OCR gets wrong on text that is really there. NFKC first, so a no-break space or an
"fi" ligature does not read as a missing line.

Compare each text-layer line against every OCR line on the same page, and against every run
of up to three consecutive OCR lines joined together, because OCR splits and merges lines in
both directions. Score with `rapidfuzz.fuzz.partial_ratio`, which lets a text-layer line
align against part of a longer OCR line.

If that fails, try `fuzz.token_set_ratio` against the same candidates. It forgives dropped
and reordered words that `partial_ratio` penalises, and rescues a line whose ending OCR lost.
The line is reported only if both fail.

Skip lines shorter than 12 normalised characters. At that length the score is dominated by
noise: "AWS" against a misread "AVS" scores 67, which would flag a real line.

**The similarity floor is 72 out of 100.**

## The measurement behind 72

Measured over the committed fixtures in `packages/integrity/tests/fixtures`, reporting the
best alignment score for every comparable line:

| Fixture | Comparable lines | Worst line score |
| --- | --- | --- |
| clean-resume.pdf | 13 | 100 |
| clean-two-page.pdf | 13 | 100 |
| injected-unicode.pdf | 14 | 98 |
| injected-homoglyphs.pdf | 13 | 86 |
| injected-invisible.pdf | 14 | **49** |
| injected-low-contrast.pdf | 14 | **49** |
| injected-micro-type.pdf | 14 | **49** |
| injected-occluded.pdf | 14 | **49** |

Injected lines score 49. The worst line that should not be flagged scores 86 — a homoglyph
line, where OCR reads the Cyrillic lookalikes as their Latin twins and so nearly agrees with
the text layer, which is the correct outcome for D6 because D5 owns that attack.

72 sits between the two, closer to the legitimate side than the midpoint. Moving it to 60
would still catch everything here; moving it to 85 would flag the homoglyph line twice.

`test_the_margin_between_clean_and_injected_text_still_holds` asserts the gap directly rather
than asserting the consequences of the floor, so a change to normalisation or candidate
joining that narrows the margin fails before a false positive reaches anyone.

## Consequences

**The clean side of this measurement is optimistic and 72 will move.** These fixtures are
synthetic PDFs rendered from clean vector text, which Tesseract reads perfectly at 200 DPI —
every clean line scored exactly 100, with no spread at all. Real resumes will not do that.
Two-column layouts, Canva and Word template exports, and scanned documents with an OCR layer
all produce legitimate scores well below 100. The margin measured here is 37 points wide;
against a real corpus it will be far narrower, and the floor will need retuning downward.

That retuning is phase 4 work and needs a corpus the fixtures cannot stand in for. Until
then, 72 is a starting point supported by a measurement, not a validated threshold, and the
README must not quote a false positive rate derived from these fixtures.

`alignment_scores` is public for exactly this reason: the evaluation harness needs the raw
scores to retune the floor, and the threshold is an empirical choice rather than a constant.

Joining up to three consecutive OCR lines makes the candidate list roughly four times the
line count. On a one-page resume that is a few hundred short-string comparisons and does not
register against the cost of the OCR pass that produced them.
