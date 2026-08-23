COMPOSE := docker compose --env-file .env -f infra/docker-compose.yml

.PHONY: dev down logs test lint migrate eval

dev: .env
	$(COMPOSE) up --build -d
	$(COMPOSE) ps

.env:
	cp .env.example .env

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api worker

test: test-api test-integrity test-worker test-web

test-api:
	$(COMPOSE) exec api pytest /srv/api

# Each suite is a separate pytest run. All three have a directory called tests, so a single
# invocation from the repo root cannot tell their conftest modules apart.
test-integrity:
	pytest packages/integrity/tests

test-worker:
	pytest worker/tests

lint: lint-python lint-web

lint-python:
	ruff check .
	ruff format --check .
	mypy api/careerlayer_api api/tests
	mypy packages/integrity
	mypy worker/careerlayer_worker worker/tests

lint-web:
	cd web && npm run lint && npm run typecheck

test-web:
	cd web && npm test

migrate:
	$(COMPOSE) exec api alembic -c /srv/api/alembic.ini upgrade head

eval:
	@echo "The eval corpus and metrics report land in phase 4; see eval/README.md."
	@exit 1
