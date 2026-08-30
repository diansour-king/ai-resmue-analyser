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

# Each suite is a separate pytest run on the host against the stack's published ports. All
# three tests directories share the name `tests`, so a single invocation from the repo root
# cannot tell their conftest modules apart; and `api/tests` imports `careerlayer_worker`,
# which the API image deliberately does not carry. The stack must be up (`make dev`).
test-api:
	pytest api/tests

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
