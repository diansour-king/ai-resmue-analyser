#!/bin/sh
# Render's free tier has no background-worker plan, so one web service runs both the API and
# the RQ worker. Used as the Docker Command in render.yaml; kept as a file so there is no
# shell quoting to get wrong in the blueprint.
#
# Deliberately not `set -e`. This script is a container entrypoint: exiting non-zero here
# does not surface an error anywhere useful, it just restarts the container, and a service
# that crash-loops on a transient database hiccup reports "Application loading" forever with
# no indication of why. Every step is logged and the failures that are survivable are
# survived.
set -u

log() { echo "[start-web] $*"; }

log "booting; PORT=${PORT:-8000} ENVIRONMENT=${ENVIRONMENT:-unset}"

# 1. Migrations. Retried, because the database is commonly still accepting connections a few
#    seconds after this container is scheduled. If they still fail, start anyway: a running
#    API with a failing readiness probe is diagnosable from the logs, a restart loop is not.
attempt=1
until alembic -c /srv/api/alembic.ini upgrade head; do
  if [ "$attempt" -ge 5 ]; then
    log "ERROR migrations failed after $attempt attempts; starting the API anyway so that"
    log "ERROR /health/ready can report which dependency is down"
    break
  fi
  log "migration attempt $attempt failed; retrying in 5s"
  attempt=$((attempt + 1))
  sleep 5
done
[ "$attempt" -lt 5 ] && log "migrations up to date"

# 2. The RQ worker, in the background.
#
#    RUN_WORKER=false is the escape hatch. The worker image carries PyMuPDF and Tesseract,
#    and rendering a page at 200 DPI is memory-hungry; on a 512 MB instance that can OOM the
#    container and take uvicorn down with it. Setting RUN_WORKER=false in the Render
#    dashboard keeps the API serving (sign-in, browsing) while uploads simply stay queued,
#    which is a far better failure mode than the whole service being unreachable.
if [ "${RUN_WORKER:-true}" = "true" ]; then
  log "starting the rq worker in the background"
  python -m careerlayer_worker.main &
else
  log "RUN_WORKER=${RUN_WORKER}; skipping the rq worker (uploads will stay queued)"
fi

# 3. uvicorn in the foreground, so it is the process the platform watches and signals.
log "starting uvicorn"
exec uvicorn careerlayer_api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
