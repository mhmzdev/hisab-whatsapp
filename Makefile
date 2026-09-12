.DEFAULT_GOAL := help

.PHONY: help up dev down down-v logs restart check sample demo stdin check-endpoint bakeoff shell landing landing-check landing-serve

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: HISAB_VAULT ?= ./vault
up: ## Docker up against your local ledger (default ./vault). Override: make up HISAB_VAULT=/path/to/folder
	HISAB_VAULT=$(HISAB_VAULT) docker compose up -d --build

dev: HISAB_VAULT ?= ./sample-vault
dev: HISAB_CONFIG ?= ./config-dev.yaml
dev: ## Docker up against the sample ledger with the OpenRouter sponsor config. Override: make dev HISAB_VAULT=/path/to/folder HISAB_CONFIG=/path/to/config.yaml
	HISAB_VAULT=$(HISAB_VAULT) HISAB_CONFIG=$(HISAB_CONFIG) docker compose up -d --build

down: ## Docker down, keep state
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

landing-serve: ## Serve the built landing page locally at http://localhost:5000
	cd landing/out && python3 -m http.server 5000
