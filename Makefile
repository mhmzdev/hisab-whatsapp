.DEFAULT_GOAL := help

.PHONY: help up dev down down-v logs restart check sample demo stdin check-endpoint bakeoff shell landing landing-check landing-serve landing-up landing-down

# 3030 dev server, 3031 Firebase Hosting emulator (firebase.json). 5000 is macOS AirPlay.
LANDING_PORT ?= 3030
LANDING_PID  := .landing-server.pid

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: HISAB_VAULT ?= ./vault
up: landing landing-up ## Worker (Docker) + landing page, both live. Override: make up HISAB_VAULT=/path/to/folder LANDING_PORT=5050
	HISAB_VAULT=$(HISAB_VAULT) docker compose up -d --build
	@echo "worker  → docker compose (make logs)"
	@echo "landing → http://localhost:$(LANDING_PORT)"

dev: HISAB_VAULT ?= ./sample-vault
dev: HISAB_CONFIG ?= ./config-dev.yaml
dev: ## Docker up against the sample ledger with the OpenRouter sponsor config. Override: make dev HISAB_VAULT=/path/to/folder HISAB_CONFIG=/path/to/config.yaml
	HISAB_VAULT=$(HISAB_VAULT) HISAB_CONFIG=$(HISAB_CONFIG) docker compose up -d --build

down: landing-down ## Docker down and stop the landing page, keep state
	docker compose down

down-v: ## Docker down and wipe the store (next message starts setup from zero)
	docker compose down -v

logs: ## Follow container logs
	docker compose logs -f

restart: up ## Rebuild and restart against your local ledger (alias for up)

shell: ## Peek at the mounted vault and message store inside the container
	docker compose exec -T hisab sh -c 'ls /app/vault; cat /app/data/messages.jsonl'

check: ## Run the no-network smoke test
	python3 tests/smoke.py

sample: ## Regenerate the committed sample ledger
	python3 tests/make_sample.py

demo: ## Terminal demo on a copy of the sample (needs a model key in .env)
	bash tests/demo_terminal.sh

stdin: ## Terminal mode on the configured ledger (python3 -m hisab.loop --stdin)
	python3 -m hisab.loop --stdin

check-endpoint: ## Validate a pasted key: model, tools, transcription. Pass ARGS="--audio note.ogg"
	python3 tests/check_endpoint.py $(ARGS)

bakeoff: ## Compare a model on the fixed demo script: make bakeoff MODEL=anthropic/claude-haiku-4.5
	bash tests/bakeoff.sh $(MODEL)

landing: ## Build the Hosted Hisab landing page and portal shell to landing/out
	cd landing && npm install && npm run build

landing-check: ## Run the landing static checks (three languages, verification direction, no payment collection)
	python3 tests/check_landing.py

landing-serve: ## Serve the built landing page in the foreground (Ctrl-C to stop)
	cd landing/out && python3 -m http.server $(LANDING_PORT)

landing-up: ## Serve the built landing page in the background (LANDING_PORT, default 3030)
	@test -d landing/out || { echo "landing/out missing — run 'make landing' first"; exit 1; }
	@if [ -f $(LANDING_PID) ] && kill -0 `cat $(LANDING_PID)` 2>/dev/null; then \
		echo "landing already serving on $(LANDING_PORT) (pid `cat $(LANDING_PID)`)"; \
	elif lsof -ti :$(LANDING_PORT) >/dev/null 2>&1; then \
		echo "port $(LANDING_PORT) is in use by something else — retry with: make up LANDING_PORT=<free port>"; exit 1; \
	else \
		cd landing/out && { nohup python3 -m http.server $(LANDING_PORT) >$(CURDIR)/.landing-server.log 2>&1 & echo $$! >$(CURDIR)/$(LANDING_PID); }; \
		sleep 1; \
	fi

landing-down: ## Stop the background landing page server
	@if [ -f $(LANDING_PID) ]; then kill `cat $(LANDING_PID)` 2>/dev/null; rm -f $(LANDING_PID); echo "landing stopped"; else echo "landing not running"; fi
