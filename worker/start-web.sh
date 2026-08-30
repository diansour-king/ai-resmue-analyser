#!/bin/sh
# Render free tier has no background-worker plan, so one web service runs both the API and
# the RQ worker. Used as the Docker Command in render.yaml; kept as a file so there is no
# shell quoting to get wrong in the blueprint.
set -e

alembic -c /srv/api/alembic.ini upgrade head

python -m careerlayer_worker.main &

exec uvicorn careerlayer_api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
