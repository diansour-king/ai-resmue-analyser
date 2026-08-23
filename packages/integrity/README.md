# careerlayer-integrity

Reads a PDF twice — once the way a machine reads it, once the way a human sees it — and
reports the difference.

This package depends on nothing above it. No FastAPI, no SQLAlchemy, no database, no web
framework. It takes a path and returns `Finding` objects, and it runs from a command line
with no server and no infrastructure. See `docs/decisions/0001-monorepo-and-polyglot-split.md`
for why that boundary is enforced rather than merely intended.

## Requirements

Python 3.11 or newer, and the `tesseract-ocr` system package. Tesseract is not a Python
dependency and `pip install` will not provide it:

```
apt-get install tesseract-ocr      # Debian and Ubuntu
brew install tesseract             # macOS
```

Without it the package still runs, five of the six detectors still work, and the CLI says so
in its output rather than silently reporting a clean document.

## Use

```
pip install -e packages/integrity
python -m careerlayer.integrity resume.pdf
python -m careerlayer.integrity resume.pdf --json
python -m careerlayer.integrity resume.pdf --detectors D1 D6
python -m careerlayer.integrity resume.pdf --no-ocr
```

Exit code is 0 when nothing above `info` was found and 1 otherwise, so this is usable as a
pipeline check without parsing its output.

As a library:

```python
from careerlayer.integrity import parse, run

findings = run(parse(Path("resume.pdf")))
```

## Detectors

| ID | Name | Signal |
| --- | --- | --- |
| D1 | Invisible render mode | Text render mode 3, cross-checked against the shape of a scanned page so an OCR layer is reported as info rather than as an attack |
| D2 | Low-contrast text | WCAG contrast against the page, with fill opacity folded in |
| D3 | Micro type | Font size below a readability floor |
| D4 | Off-canvas or occluded text | Outside the crop box, or buried under an image drawn after it |
| D5 | Unicode anomalies | Zero-width characters, bidi overrides, and words mixing Latin with a lookalike script |
| D6 | Extraction delta | Text-layer lines the rendered page does not corroborate |

Each is a module with a `detect(document) -> list[Finding]` function. They are independent:
none sees another's output, and any subset can be run alone.

## What it does not do

It reports. It does not reject, score, or rank a candidate, and it never will — findings are
advisory and are always surfaced to a person. A false flag costs someone a job, so every
threshold in this package is tuned toward missing an attack rather than inventing one.

Detection raises the cost of an attack. It does not eliminate it. The thresholds here were
measured against synthetic fixtures and will need retuning against a real corpus in phase 4;
until then no false positive rate derived from them should be published.

## Tests and fixtures

```
pytest packages/integrity/tests
```

Fixtures are small hand-built PDFs in `tests/fixtures`, committed rather than generated at
test time so a failing test points at a detector rather than at the generator, and so a
reviewer can open the artefact the tests actually saw. `tests/build_fixtures.py` regenerates
them and needs a Unicode TrueType font for the two Unicode cases.

The attack samples here are synthetic and exist to test this system. They are never sent to
any real company's hiring pipeline.
