FROM python:3.11-slim

# Tesseract is a system package, not a Python dependency. The worker is the only service
# that runs OCR, so it is the only image that carries it: the API writes a row and returns.
RUN (sed -i 's/http:/https:/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/http:/https:/g' /etc/apt/sources.list 2>/dev/null || true) \
 && apt-get update \
 && apt-get install --no-install-recommends -y tesseract-ocr libgl1 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY packages/integrity /srv/packages/integrity
COPY packages/scoring /srv/packages/scoring
COPY api /srv/api
COPY worker /srv/worker

RUN pip install -e /srv/packages/integrity \
 && pip install -e /srv/packages/scoring \
 && pip install -e /srv/api \
 && pip install -e /srv/worker

CMD ["python", "-m", "careerlayer_worker.main"]
