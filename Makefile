# stacksmith - deployment kit for the docubot stack

.DEFAULT_GOAL := help
COMPOSE := docker compose -f docker-compose.infra.yml -f docker-compose.prod.yml -f docker-compose.override.yml

.PHONY: help up down logs ps lint doctor certs

help: ## list available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## bring the stack up and wait for every service
	bash scripts/check-env.sh
	$(COMPOSE) up -d --wait

down: ## stop and remove the stack
	$(COMPOSE) down --remove-orphans

logs: ## tail stack logs
	$(COMPOSE) logs -f --tail=100

ps: ## show stack status
	$(COMPOSE) ps

lint: ## run yamllint and shellcheck locally
	yamllint .
	@for f in scripts/*.sh; do [ -e "$$f" ] || continue; shellcheck -x "$$f"; done

doctor: ## check the host is ready to run the stack
	bash scripts/doctor.sh

certs: ## generate a self-signed dev certificate pair (never for production)
	mkdir -p nginx/certs
	openssl req -x509 -newkey rsa:2048 -sha256 -days 30 -nodes \
		-keyout nginx/certs/privkey.pem -out nginx/certs/fullchain.pem \
		-subj "/CN=localhost" 2>/dev/null
	@echo "dev certificates written to nginx/certs/"
