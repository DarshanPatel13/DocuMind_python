# DocuMind developer tasks. `make help` lists everything.
# (On Windows, run these from Git Bash, or use the underlying commands directly.)

.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help up down logs build ps test seed eval

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

up: ## Build + start the whole stack (gateway:8080, frontend:5173)
	$(COMPOSE) up --build -d
	@echo "Frontend  http://localhost:5173   Gateway  http://localhost:8080"
	@echo "Login: demo / demo12345"

down: ## Stop the stack (keep volumes)
	$(COMPOSE) down

logs: ## Tail logs for all services
	$(COMPOSE) logs -f

ps: ## Show running containers
	$(COMPOSE) ps

build: ## Build all images without starting
	$(COMPOSE) build

test: ## Run every service's unit tests (in containers)
	$(COMPOSE) run --rm --no-deps document-service pytest -q
	$(COMPOSE) run --rm --no-deps query-service pytest -q
	$(COMPOSE) run --rm --no-deps gateway pytest -q

seed: ## Upload the sample PDFs in ./samples (placeholder for Day 1)
	@echo "Drop PDFs in ./samples and POST them to the gateway — see docs/runbook.md"

eval: ## RAG evaluation suite (added on Day 2)
	@echo "make eval is wired up on Day 2 (Ragas). See docs/ai/evaluation.md"
