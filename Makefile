# stacksmith - deployment kit for the docubot stack

.DEFAULT_GOAL := help
SMOKE := docker compose -f tests/smoke/docker-compose.yml

.PHONY: help up down logs ps lint doctor

help: ## list available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## bring the stack up and wait for health
	$(SMOKE) up -d --wait

down: ## stop and remove the stack
	$(SMOKE) down --remove-orphans

logs: ## tail stack logs
	$(SMOKE) logs -f --tail=100

ps: ## show stack status
	$(SMOKE) ps

lint: ## run yamllint and shellcheck locally
	yamllint .
	@for f in scripts/*.sh; do [ -e "$$f" ] || continue; shellcheck -x "$$f"; done

doctor: ## check the host is ready to run the stack
	bash scripts/doctor.sh
