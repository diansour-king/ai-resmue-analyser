# worker

The RQ worker that turns an uploaded PDF into pages, spans, findings and skills.

It is a separate deployable from the API because their scaling shapes differ: the API is
IO-bound and small, the worker is CPU-bound, holds a whole page raster in memory, and is the
only service that needs Tesseract installed.

```
python -m careerlayer_worker.main
```

The pipeline is `careerlayer_worker.pipeline.process_resume`, enqueued by the API by dotted
path rather than by import, so the API image never pulls in the analysis stack.

D1 to D6 are not implemented here. They live in `packages/integrity` and are called from it.
