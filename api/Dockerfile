FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY packages/scoring /srv/packages/scoring
COPY api /srv/api

# Editable, so the bind mount declared in infra/docker-compose.yml shadows the copied
# source and code changes take effect without a rebuild. Phase 5 builds the production
# image from a separate stage without --reload and without the dev extra.
RUN pip install -e /srv/packages/scoring \
 && pip install -e "/srv/api[dev]"

CMD ["uvicorn", "careerlayer_api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--reload", "--reload-dir", "/srv/api/careerlayer_api"]
