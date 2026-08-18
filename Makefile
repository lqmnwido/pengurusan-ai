
ifneq ($(shell which docker-compose 2>/dev/null),)
    DOCKER_COMPOSE := docker-compose
else
    DOCKER_COMPOSE := docker compose
endif

.DEFAULT_GOAL := help

.PHONY: help setup dev build serve agent-worker openclaw-setup openclaw-agentic-mcp deploy install remove start startAndBuild stop update

help:
	@printf '%s\n' \
		'Pengurusan AI commands' \
		'' \
		'Native (recommended; no Docker)' \
		'  make setup           Create .env/.venv and install backend, frontend, and OpenClaw dependencies' \
		'  make dev             Run frontend, API, and the Temporal agent worker when enabled' \
		'  make build           Build the production frontend into build/' \
		'  make serve           Serve the built frontend and API on :8080' \
		'  make agent-worker    Run the Pengurusan AI Temporal worker' \
		'  make openclaw-setup  Run one-time OpenClaw provider/auth onboarding' \
		'  make openclaw-agentic-mcp AGENT_ID=<id>  Expose assigned Agentic AI tools to one OpenClaw agent' \
		'  make deploy          Run setup and build for a native production deployment' \
		'' \
		'Docker (legacy/upstream workflow)' \
		'  make install         Start services with Docker Compose' \
		'  make start           Start existing Docker Compose services' \
		'  make startAndBuild   Build and start Docker Compose services' \
		'  make stop            Stop Docker Compose services' \
		'  make remove          Remove the Docker deployment after confirmation' \
		'  make update          Update Ollama models/source and rebuild Docker services'

# Native (non-Docker) workflow
setup:
	@./scripts/setup-native.sh

dev:
	@./scripts/dev-native.sh

build:
	@./scripts/build-native.sh

serve:
	@./scripts/serve-production.sh

agent-worker:
	@./scripts/agent-worker.sh

openclaw-setup:
	@./scripts/openclaw-setup.sh

openclaw-agentic-mcp:
	@./scripts/openclaw-agentic-mcp.sh

deploy: setup build

# Docker workflow
install:
	$(DOCKER_COMPOSE) up -d

remove:
	@chmod +x confirm_remove.sh
	@./confirm_remove.sh

start:
	$(DOCKER_COMPOSE) start
startAndBuild: 
	$(DOCKER_COMPOSE) up -d --build

stop:
	$(DOCKER_COMPOSE) stop

update:
	# Calls the LLM update script
	chmod +x update_ollama_models.sh
	@./update_ollama_models.sh
	@git pull
	$(DOCKER_COMPOSE) down
	# Make sure the ollama-webui container is stopped before rebuilding
	@docker stop open-webui || true
	$(DOCKER_COMPOSE) up --build -d
	$(DOCKER_COMPOSE) start
