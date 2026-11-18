# stacksmith - deployment kit for the docubot stack

.DEFAULT_GOAL := help
PROD := docker compose -f docker-compose.prod.yml
STUB := docker compose -f tests/smoke/docker-compose.yml

.PHONY: help up down logs ps deploy rollback backup restore doctor lint test test-quick smoke smoke-stub demo

help: ## list available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## bring the prod stack up and wait for health
	$(PROD) up -d --build --wait

down: ## stop and remove the prod stack
	$(PROD) down --remove-orphans

logs: ## tail prod stack logs
	$(PROD) logs -f --tail=200

ps: ## show prod stack status
	$(PROD) ps

deploy: ## blue-green deploy (phase 2)
	@bash scripts/deploy.sh "$$DEPLOY_COLOR"

rollback: ## roll back to the previous release (phase 2)
	@bash scripts/rollback.sh

backup: ## take a database backup (phase 3)
	@bash scripts/backup-db.sh

restore: ## restore the database from a backup file (phase 3)
	@bash scripts/restore-db.sh "$$BACKUP_FILE"

doctor: ## check the host is ready to run the stack
	@bash scripts/doctor.sh

lint: ## run yamllint and shellcheck locally
	yamllint .
	@for f in scripts/*.sh; do [ -e "$$f" ] || continue; shellcheck -x "$$f"; done

test: ## run the Django unit suite locally (matches CI's unit.yml)
	@# Install only the unit-test dep subset — torch and
	@# sentence-transformers are multi-hundred-MB wheels and are
	@# lazy imports; the suite exercises the embedding layer through
	@# its documented stub provider. The venv is created if missing.
	@if ! command -v python3 >/dev/null 2>&1; then \
		echo "python3 not found"; exit 1; \
	fi
	@VENV=$${VENV:-$$(python3 -c 'import sys,os; print(os.path.expanduser("~/.venv"))')}; \
	if [ ! -x "$$VENV/bin/python" ]; then \
		echo "creating venv at $$VENV"; \
		python3 -m venv "$$VENV"; \
	fi; \
	TMPREQ=$$(mktemp); \
	grep -vE '^(torch|sentence-transformers)==' app/requirements.txt > $$TMPREQ; \
	$$VENV/bin/python -m pip install -q --disable-pip-version-check \
		-r $$TMPREQ pytest==8.3.3 markdown 2>/dev/null; \
	rm -f $$TMPREQ; \
	echo "running pytest..."; \
	DJANGO_SETTINGS_MODULE=config.settings \
		$$VENV/bin/python -m pytest app/tests -v --tb=short $${PYTEST_ARGS:-}

test-quick: ## run the unit suite but stop at the first failure
	@$(MAKE) --no-print-directory test PYTEST_ARGS="-x -q"

smoke: ## local smoke test — bring the prod stack up and probe /health
	cp -n .env.example .env 2>/dev/null || true
	$(PROD) up -d --build --wait
	@curl -fsS http://127.0.0.1:8080/health/live/ && echo ""
	$(PROD) down --remove-orphans -v

smoke-stub: ## quick stub stack smoke
	$(STUB) up -d --wait
	@curl -fsS http://127.0.0.1:8080/health && echo ""
	$(STUB) down --remove-orphans

demo: ## ingest the sample corpus and run a query through the chat API
	@python3 scripts/demo.py
