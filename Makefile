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
	$(COMPOSE) logs -f api

test: test-api test-integrity

test-api:
	$(COMPOSE) exec api pytest /srv/api

# Runs on the host rather than in the api container: the integrity package needs the
# tesseract binary, which that image does not carry until the worker is built in phase 2.
test-integrity:
	pytest packages/integrity/tests

lint:
	ruff check .
	ruff format --check .
	mypy api/careerlayer_api packages/integrity

migrate:
	$(COMPOSE) exec api alembic -c /srv/api/alembic.ini upgrade head

eval:
	@echo "The eval corpus and metrics report land in phase 4; see eval/README.md."
	@exit 1
