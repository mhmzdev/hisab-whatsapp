.DEFAULT_GOAL := help

.PHONY: help selfhost selfhost-dev selfhost-down selfhost-down-v selfhost-logs selfhost-restart selfhost-shell up dev down down-v check sample demo stdin check-endpoint bakeoff landing landing-pages landing-pages-sync landing-pages-deploy landing-check landing-serve landing-up landing-down rules-test emulators emulators-up emulators-down runner-up runner-logs runner-down runner-down-v

# 3030 self-host landing server, 3031 Firebase Hosting emulator (firebase.json). 5000 is macOS AirPlay.
LANDING_PORT ?= 3030
LANDING_PID  := .landing-server.pid

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

selfhost: HISAB_VAULT ?= ./vault
selfhost: landing landing-up ## Self-host worker (Docker) + landing page, both live. Override: make selfhost HISAB_VAULT=/path/to/folder LANDING_PORT=5050
	HISAB_VAULT=$(HISAB_VAULT) docker compose up -d --build
	@echo "worker  → docker compose (make selfhost-logs)"
	@echo "landing → http://localhost:$(LANDING_PORT)"

selfhost-dev: HISAB_VAULT ?= ./sample-vault
selfhost-dev: HISAB_CONFIG ?= ./config-dev.yaml
selfhost-dev: ## Self-host worker against the sample ledger with the OpenRouter sponsor config. Override: make selfhost-dev HISAB_VAULT=/path/to/folder HISAB_CONFIG=/path/to/config.yaml
	HISAB_VAULT=$(HISAB_VAULT) HISAB_CONFIG=$(HISAB_CONFIG) docker compose up -d --build

selfhost-down: landing-down ## Self-host Docker down and stop the landing page, keep state
	docker compose down

selfhost-down-v: ## Self-host Docker down and wipe the store (next message starts setup from zero)
	docker compose down -v

selfhost-logs: ## Follow self-host container logs
	docker compose logs -f

selfhost-restart: selfhost ## Rebuild and restart the self-host worker against your local ledger (alias for selfhost)

selfhost-shell: ## Peek at the self-host mounted vault and message store inside the container
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

landing: NEXT_PUBLIC_USE_EMULATORS ?= 1
landing: NEXT_PUBLIC_HOSTED ?= 0
landing: ## Build the landing page and portal to landing/out; hosted sign-up off (the public build). Override: NEXT_PUBLIC_HOSTED=1, NEXT_PUBLIC_USE_EMULATORS=0
	cd landing && npm install && NEXT_PUBLIC_USE_EMULATORS=$(NEXT_PUBLIC_USE_EMULATORS) NEXT_PUBLIC_HOSTED=$(NEXT_PUBLIC_HOSTED) npm run build

# GitHub Pages: the public landing under PAGES_BASE_PATH on mhmzdev.github.io, hosted sign-up off. Built into
# landing/out-pages so landing/out (what the emulators serve) is never overwritten.
PAGES_BASE_PATH ?= /hisab
PAGES_DIR ?= ../mhmzdev.github.io

landing-pages: ## Build the public GitHub Pages landing into landing/out-pages (hosted off, under PAGES_BASE_PATH=/hisab)
	cd landing && npm install && NEXT_PUBLIC_BASE_PATH=$(PAGES_BASE_PATH) NEXT_PUBLIC_HOSTED=0 NEXT_PUBLIC_USE_EMULATORS=0 NEXT_DIST_DIR=out-pages npm run build

landing-pages-sync: landing-pages ## Copy that build into PAGES_DIR (../mhmzdev.github.io)$(PAGES_BASE_PATH) with .nojekyll; commit and push there yourself
	@test -d $(PAGES_DIR)/.git || { echo "$(PAGES_DIR) is not a git checkout — clone mhmzdev/mhmzdev.github.io there or pass PAGES_DIR=<path>"; exit 1; }
	rsync -a --delete landing/out-pages/ $(PAGES_DIR)$(PAGES_BASE_PATH)/
	touch $(PAGES_DIR)/.nojekyll   # Jekyll would drop _next/, which holds every script and stylesheet
	@echo "synced → $(PAGES_DIR)$(PAGES_BASE_PATH)/  (git -C $(PAGES_DIR) status)"

# Publishing is deliberate: only from a clean, pushed main (the commit names what went live), only the hisab/ folder
# and .nojekyll are staged (the other sites in that repo are never swept in), and nothing is pushed when nothing changed.
landing-pages-deploy: ## Build, sync, commit and push the GitHub Pages landing (from a clean main that matches origin)
	@test "`git branch --show-current`" = main || { echo "deploy from main — you are on `git branch --show-current`"; exit 1; }
	@test -z "`git status --porcelain --untracked-files=no`" || { echo "commit or stash your changes first: the deploy names a commit"; exit 1; }
	@git fetch -q origin main && test "`git rev-parse HEAD`" = "`git rev-parse origin/main`" || { echo "local main differs from origin/main — pull or push first"; exit 1; }
	@test -z "`git -C $(PAGES_DIR) status --porcelain -- $(PAGES_BASE_PATH:/%=%) .nojekyll`" || { echo "$(PAGES_DIR) has uncommitted changes under $(PAGES_BASE_PATH) — look before deploying over them"; exit 1; }
	$(MAKE) landing-pages-sync
	git -C $(PAGES_DIR) add -- $(PAGES_BASE_PATH:/%=%) .nojekyll
	@if git -C $(PAGES_DIR) diff --cached --quiet; then echo "nothing changed on the page; not committing"; else \
		git -C $(PAGES_DIR) commit -q -m "hisab: deploy `git rev-parse --short HEAD`" -- $(PAGES_BASE_PATH:/%=%) .nojekyll && \
		git -C $(PAGES_DIR) push -q && echo "pushed → https://mhmzdev.github.io$(PAGES_BASE_PATH)/ (live in a minute or two)"; fi

landing-check: ## Run the landing static checks (en and ur, verification direction, no payment collection)
	python3 tests/check_landing.py

# ---- hosted mode: local profile (emulators on the host, runner in Docker, portal from landing/out) ----
# 3031 serves landing/out through the Hosting emulator; auth 9099 and firestore 8080 are in firebase.json.
FIREBASE_PROJECT ?= demo-hisab
EMULATORS_PID := .emulators.pid
# Auth users and Firestore tenants survive a restart: imported on start, exported on a clean stop. Wiped by make down-v.
EMULATOR_DATA := ./emulator-data
EMULATOR_FLAGS := --only auth,firestore,hosting --project $(FIREBASE_PROJECT) --import=$(EMULATOR_DATA) --export-on-exit=$(EMULATOR_DATA)

up: NEXT_PUBLIC_HOSTED := 1
up: landing emulators-up runner-up ## Hosted local stack: Gemini runner + Auth/Firestore/Hosting emulators + portal at :3031
	@echo "OTPs → tail -f firebase-debug.log, or: curl http://localhost:9099/emulator/v1/projects/$(FIREBASE_PROJECT)/verificationCodes"

down: runner-down emulators-down ## Stop the hosted local stack, keep runner-data/
down-v: runner-down-v emulators-down ## Stop the hosted local stack AND wipe runner-data/ and emulator-data/
	rm -rf $(EMULATOR_DATA)

dev: NEXT_PUBLIC_USE_EMULATORS := 0
dev: RUNNER_CONFIG ?= ./runner/config-dev.yaml
dev: RUNNER_SERVICE_ACCOUNT ?= ./service-account.json
dev: ## Hosted dev-profile stack: OpenRouter runner against the dev Firebase project, portal built with emulators off
	@test -f $(RUNNER_SERVICE_ACCOUNT) || { echo "$(RUNNER_SERVICE_ACCOUNT) missing — the dev Firebase project isn't provisioned yet"; exit 1; }
	@test -f $(RUNNER_CONFIG) || { echo "$(RUNNER_CONFIG) missing — cp examples/runner-config.openrouter.yaml $(RUNNER_CONFIG)"; exit 1; }
	@grep -q '^RUNNER_PRIVATE_KEY=.\+' .env || { echo "RUNNER_PRIVATE_KEY missing from .env — python3 -m runner.keygen"; exit 1; }
	$(MAKE) landing NEXT_PUBLIC_USE_EMULATORS=$(NEXT_PUBLIC_USE_EMULATORS) NEXT_PUBLIC_HOSTED=1
	RUNNER_CONFIG=$(RUNNER_CONFIG) RUNNER_SERVICE_ACCOUNT=$(RUNNER_SERVICE_ACCOUNT) env -u FIRESTORE_EMULATOR_HOST docker compose -f docker-compose.runner.yml -f docker-compose.runner.dev.yml up -d --build
	@echo "runner (dev) → docker compose -f docker-compose.runner.yml -f docker-compose.runner.dev.yml"

emulators: ## Auth + Firestore + Hosting emulators in the foreground (demo project; OTPs print here). Run `make landing` first
	@test -d landing/out || { echo "landing/out missing — run 'make landing' first"; exit 1; }
	@mkdir -p $(EMULATOR_DATA)
	firebase emulators:start $(EMULATOR_FLAGS)

emulators-up: ## Auth + Firestore + Hosting emulators in the background (demo project; OTPs land in firebase-debug.log). Run `make landing` first
	@test -d landing/out || { echo "landing/out missing — run 'make landing' first"; exit 1; }
	@if [ -f $(EMULATORS_PID) ] && kill -0 `cat $(EMULATORS_PID)` 2>/dev/null; then \
		echo "emulators already running (pid `cat $(EMULATORS_PID)`)"; \
	elif lsof -ti :3031 >/dev/null 2>&1; then \
		echo "port 3031 is in use by something else"; exit 1; \
	else \
		mkdir -p $(EMULATOR_DATA); \
		nohup firebase emulators:start $(EMULATOR_FLAGS) >firebase-debug.log 2>&1 & echo $$! >$(EMULATORS_PID); \
		sleep 2; \
	fi

emulators-down: ## Stop the background emulators, saving Auth and Firestore to emulator-data/ first
	@if [ -f $(EMULATORS_PID) ] && kill -0 `cat $(EMULATORS_PID)` 2>/dev/null; then \
		mkdir -p $(EMULATOR_DATA); \
		firebase emulators:export $(EMULATOR_DATA) --project $(FIREBASE_PROJECT) --force >>firebase-debug.log 2>&1 \
			|| echo "export failed — see firebase-debug.log; relying on export-on-exit"; \
		pid=`cat $(EMULATORS_PID)`; kill -INT $$pid; \
		for i in `seq 60`; do kill -0 $$pid 2>/dev/null || break; sleep 0.5; done; \
		if kill -0 $$pid 2>/dev/null; then kill $$pid; echo "emulators did not stop in 30s; killed"; else echo "emulators stopped, data in $(EMULATOR_DATA)"; fi; \
		rm -f $(EMULATORS_PID); \
	else rm -f $(EMULATORS_PID); echo "emulators not running"; fi

runner-up: RUNNER_CONFIG ?= ./runner/config.yaml
runner-up: ## Runner in Docker against the local emulators, on RUNNER_CONFIG (default Gemini). Needs RUNNER_CONFIG and RUNNER_PRIVATE_KEY in .env
	@test -f $(RUNNER_CONFIG) || { echo "$(RUNNER_CONFIG) missing — cp runner/config.example.yaml $(RUNNER_CONFIG)"; exit 1; }
	@grep -q '^RUNNER_PRIVATE_KEY=.\+' .env || { echo "RUNNER_PRIVATE_KEY missing from .env — python3 -m runner.keygen"; exit 1; }
	@docker compose -f docker-compose.yml ps -q --status running 2>/dev/null | grep -q . && { echo "self-host container is running (docker-compose.yml) — same agent token risks HTTP 409 from two pollers. Run 'make selfhost-down' first."; exit 1; } || true
	RUNNER_CONFIG=$(RUNNER_CONFIG) FIRESTORE_EMULATOR_HOST=host.docker.internal:8080 GCLOUD_PROJECT=$(FIREBASE_PROJECT) docker compose -f docker-compose.runner.yml up -d --build
	@echo "runner  → docker compose -f docker-compose.runner.yml (make runner-logs)"
	@echo "portal  → http://localhost:3031/portal/"

runner-logs: ## Follow the runner's logs (tenant transitions, worker exits, every worker's own output)
	docker compose -f docker-compose.runner.yml logs -f

runner-down: ## Stop the runner, keep every tenant's ledger and state under runner-data/
	docker compose -f docker-compose.runner.yml down

runner-down-v: ## Stop the runner AND delete runner-data/ (every tenant's ledger, state, per-tenant config and the inactive/ retention copies)
	docker compose -f docker-compose.runner.yml down
	rm -rf runner-data

rules-test: ## firestore.rules as owner and attacker, against a throwaway Firestore emulator (needs Java + firebase-tools)
	cd tests/rules && npm install
	firebase emulators:exec --only firestore --project demo-hisab-rules "cd tests/rules && npm test"

landing-serve: ## Serve the built landing page in the foreground (Ctrl-C to stop)
	cd landing/out && python3 -m http.server $(LANDING_PORT)

landing-up: ## Serve the built landing page in the background (LANDING_PORT, default 3030)
	@test -d landing/out || { echo "landing/out missing — run 'make landing' first"; exit 1; }
	@if [ -f $(LANDING_PID) ] && kill -0 `cat $(LANDING_PID)` 2>/dev/null; then \
		echo "landing already serving on $(LANDING_PORT) (pid `cat $(LANDING_PID)`)"; \
	elif lsof -ti :$(LANDING_PORT) >/dev/null 2>&1; then \
		echo "port $(LANDING_PORT) is in use by something else — retry with: make selfhost LANDING_PORT=<free port>"; exit 1; \
	else \
		cd landing/out && { nohup python3 -m http.server $(LANDING_PORT) >$(CURDIR)/.landing-server.log 2>&1 & echo $$! >$(CURDIR)/$(LANDING_PID); }; \
		sleep 1; \
	fi

landing-down: ## Stop the background landing page server
	@if [ -f $(LANDING_PID) ]; then kill `cat $(LANDING_PID)` 2>/dev/null; rm -f $(LANDING_PID); echo "landing stopped"; else echo "landing not running"; fi
