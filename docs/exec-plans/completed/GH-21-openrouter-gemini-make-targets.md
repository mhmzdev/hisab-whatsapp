---
slug: GH-21-openrouter-gemini-make-targets
issue: 21
status: completed
open_questions: none
---

# Feature: drop direct-OpenAI support, restructure `make up`/`make dev`          ✅ COMPLETED — 2026-09-13

## Problem

Three providers are wired where two are wanted, and the two make targets run the wrong stack. See
issue [#21](https://github.com/mhmzdev/hisab-whatsapp/issues/21) for the full "what's wrong" — in
short: `provider: openai` in `hisab/transcribe.py` and `examples/config.openai.yaml` have never been
the local or demo config; `agents_sdk` is a dead flag nothing reads; `make up` is the self-host stack
and runs no Firebase, so the portal can't sign in from it; `make dev` runs self-host on OpenRouter
against the sample vault, not the hosted OpenRouter profile; the portal bakes
`NEXT_PUBLIC_USE_EMULATORS` at build time so the emulator and remote builds are two builds.

## Approach

**Providers.** Drop the `openai` branch from `hisab/transcribe.py` and the `agents_sdk` flag from
every config surface. Add one validation point: `hisab/config.py:load()` rejects an unknown
`transcription.provider` with a one-line `SystemExit` (uncaught, this prints the message and exits
without a traceback — appropriate for a config error at process startup, and every `hisab.loop`
process, self-host or per-tenant, goes through this one function). `OpenAI-compatible endpoint`
stays as protocol wording; OpenRouter model ids like `openai/gpt-4.1-mini` stay.

**Runner config per profile.** `docker-compose.runner.yml` mounts `${RUNNER_CONFIG:-./runner/config.yaml}`,
mirroring how `docker-compose.yml` already follows `HISAB_CONFIG`. `runner/config.example.yaml`
becomes the Gemini profile (what `make up` uses by default); a new `examples/runner-config.openrouter.yaml`
is the OpenRouter profile, copied to a gitignored `runner/config-dev.yaml` for `make dev`. Two
examples live under `examples/` (not `runner/`) so they sit next to the existing root-level
`config.*.yaml` examples instead of splitting example configs across two directories.

**Two docker-compose files, not a hand-edited one.** Today's `docker-compose.runner.yml` asks the
operator to hand-uncomment a `dev` block for `GOOGLE_APPLICATION_CREDENTIALS` and the service-account
mount — exactly the manual step `make dev` needs to not require. Split it: the base file keeps only
the `FIRESTORE_EMULATOR_HOST`/`GCLOUD_PROJECT` pass-through (local/emulator profile, what `make up`
uses); a new `docker-compose.runner.dev.yml` layers on `GOOGLE_APPLICATION_CREDENTIALS` and the
service-account bind mount. `FIRESTORE_EMULATOR_HOST` must not be set to an empty string to "clear"
it — `google-cloud-firestore`'s own client checks `os.getenv("FIRESTORE_EMULATOR_HOST") is not None`
internally, so an empty value still routes to an emulator at host `""`; `make dev`'s recipe instead
runs `docker compose` under `env -u FIRESTORE_EMULATOR_HOST`, so a stale shell export from an earlier
`make up` in the same terminal can't leak in, and the base file's bare `- FIRESTORE_EMULATOR_HOST`
pass-through then finds nothing to pass — the variable is genuinely absent inside the container.
`runner/firestore_listener.py:20`'s own `os.environ.get("FIRESTORE_EMULATOR_HOST")` truthiness check
already treats an empty string the same as unset; that's a second, independent reason it's fine to
leave that line as-is rather than "fix" it — the real problem was only ever the compose-level env var
itself. `make dev` runs both compose files with `-f`; `make up` runs the base file alone.

**`make up` / `make dev` restructured; self-host renamed to `make selfhost`.** Today's self-host
`up`/`dev`/`down`/`down-v`/`logs`/`restart`/`shell` become `selfhost`/`selfhost-dev`/`selfhost-down`/
`selfhost-down-v`/`selfhost-logs`/`selfhost-restart`/`selfhost-shell` — same behaviour, new names,
freeing `up`/`dev`/`down`/`down-v` for the hosted stack:
- `make up` = `landing` (build, emulators on — the default) + `emulators-up` (new background variant
  of `make emulators`, same pid-file pattern as `landing-up`) + `runner-up` (Gemini, i.e. `RUNNER_CONFIG`
  defaults to `./runner/config.yaml`) + print the portal URL and where OTPs land. `make emulators`
  stays the foreground variant.
- `make down` = `runner-down` + `emulators-down`, keeping `runner-data/`. `make down-v` = `runner-down-v`
  + `emulators-down`, wiping it.
- `make dev` = fail-fast checks (service-account JSON, `RUNNER_CONFIG`, `RUNNER_PRIVATE_KEY`) *before*
  building anything, then `landing` with `NEXT_PUBLIC_USE_EMULATORS=0` (via a recursive `$(MAKE)`
  call, so the checks run first) + the runner on both compose files with `RUNNER_CONFIG` defaulting
  to `./runner/config-dev.yaml`. The dev Firebase project doesn't exist yet, so the service-account
  check fails today by construction — that's the intended state until the owner provisions it.
- `runner-up` itself gains the self-host collision guard from issue decision #7 (`docker compose -f
  docker-compose.yml ps` — refuse with a one-line message if a self-host container is running,
  pointing at `make selfhost-down`), not just `make up`: it protects every path that starts the
  runner, `make up` included, and a directly-invoked `make runner-up` too.
- `landing`'s build gets a `NEXT_PUBLIC_USE_EMULATORS` target-specific variable (default `1`), passed
  on the `npm run build` command line — GNU Make target-specific variables are inherited by
  prerequisites, so `make dev`'s override of `0` reaches `landing`'s recipe when `dev` invokes it.
  `landing/.env.local` keeps `NEXT_PUBLIC_USE_EMULATORS=1` as the default for direct `npm run build`
  or `make landing` with no override; the command-line value wins per Next.js's own env precedence
  (confirmed: an already-set process env var is not overridden by `.env.local`). `make up` and
  `make selfhost` both rebuild `landing/out` every invocation (matches today's behaviour — `make
  landing` always runs `npm install && npm run build`, no staleness check); this plan doesn't add one.

**Docs.** `AGENTS.md`'s Commands table, `runner/README.md`'s "full local loop" section and profile
table, `landing/README.md`'s command table, and `README.md`'s self-host and Hosted Hisab sections all
currently describe the old `make up`/`make dev` split. Rewrite them to match. The lead is landing a
parallel GH-5 branch touching `README.md:71`'s exact paragraph (shortening it further, dropping the
"#5–#7" reference since #7 is merging and #5 is in flight), the `runner-down-v` Makefile help line,
`runner/README.md`'s lifecycle table and Layout list (not the "full local loop" section this plan
replaces), and `AGENTS.md`'s runner/ repo-map line (not the Commands-table row this plan replaces) —
this plan's README paragraph is written short for exactly that reason, and touches none of those
other spots, so whichever branch merges second rebases cleanly.

Invariants kept: six tools (untouched), strict check (untouched), privacy (`.env`/`config.yaml`/
`runner/config.yaml`/`vault/` stay gitignored and unedited-in-docs), the runner-never-touches-WhatsApp
and worker-never-learns-Firebase boundaries (untouched — this plan only changes which config file and
which compose file the runner starts with).

## Success criteria

- [x] No OpenAI-provider or `agents_sdk` residue — `verify: grep -rniE 'provider == "openai"|OPENAI_API_KEY|agents_sdk|config\.openai' hisab runner tests examples config.example.yaml .env.example` (must return nothing, exit 1); `examples/config.openai.yaml` is gone
- [x] `transcription.provider` accepts exactly `openrouter`/`gemini`, anything else fails at config load with a one-line message — in both `hisab/config.py:load()` and `runner/config.py:load()` — `verify: python3 tests/smoke.py` (new assertions added in Phase 1)
- [x] The two runner compose profiles are syntactically valid — `verify: docker compose -f docker-compose.runner.yml config -q && docker compose -f docker-compose.runner.yml -f docker-compose.runner.dev.yml config -q`
- [x] The portal builds in both modes — `verify: cd landing && NEXT_PUBLIC_USE_EMULATORS=1 npm run build && NEXT_PUBLIC_USE_EMULATORS=0 npm run build`
- [x] `make dev` fails fast with one line naming the missing service-account file (the dev project doesn't exist yet) — `verify: manual: run "make dev" from repo root with no ./service-account.json present; expect exit 1 and a single line naming the file`
- [x] `make up` alone brings up the emulators in the background, the runner on Gemini, and the portal at http://localhost:3031/portal/; `make down` stops all of it — `verify: manual: make up; curl -sf http://localhost:3031/portal/ | grep -qi hisab; make down`
- [x] The runner refuses to start when the self-host container is running (`make up`'s only path to starting the runner is `runner-up`, which carries the guard) — `verify: manual: bring the self-host container up directly; make runner-up (expect exit 1 naming HTTP 409 and "make selfhost-down"); tear the self-host container down`
- [x] The self-host path is one command under its own name — `verify: manual: make selfhost starts docker-compose.yml (docker compose -f docker-compose.yml ps shows it running); make selfhost-down`
- [!] `check_endpoint` passes for both runner profiles with real keys — Gemini (`runner/config.yaml`) is ALL PASS; OpenRouter (`runner/config-dev.yaml`) fails on live calls with `HTTP 401 API key expired` — the same failure reproduces against the pre-existing, untouched root `config-dev.yaml`, so the sponsor `OPENROUTER_API_KEY` in `.env` has expired; unrelated to this plan's changes (key-presence and model/tools-listing checks against OpenRouter both pass) — `verify: manual: python3 tests/check_endpoint.py --config runner/config.yaml && python3 tests/check_endpoint.py --config runner/config-dev.yaml`
- [x] Docs describe the two stacks and their targets — `verify: read AGENTS.md, runner/README.md, landing/README.md, README.md`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Two providers, two validation points
**Status:** Done — smoke.py prints both new validation lines and ends ALL OK; grep is clean except `runner/config.example.yaml`'s `agents_sdk` line, which Phase 2 rewrites wholesale.
- Files:
  - `hisab/config.py:11` — drop `"agents_sdk": False` from the `model` DEFAULTS dict. In `load()` (currently `hisab/config.py:29-40`), after `cfg = _merge(DEFAULTS, raw)`, add:
    ```python
    provider = (cfg["transcription"].get("provider") or "openrouter").lower()
    if provider not in ("openrouter", "gemini"):
        raise SystemExit(f"transcription.provider must be 'openrouter' or 'gemini', got {provider!r}")
    ```
  - `runner/config.py:14` — drop `"agents_sdk": False` from the `model` DEFAULTS dict, and add the
    same check in `load()` (currently `runner/config.py:26-34`), after `cfg = _merge(DEFAULTS, raw)`,
    so a bad *runner* config fails when `make up`/`make dev` starts it rather than only when the
    first tenant worker spins up and hits `hisab/config.py`'s check instead:
    ```python
    provider = (cfg["transcription"].get("provider") or "openrouter").lower()
    if provider not in ("openrouter", "gemini"):
        raise SystemExit(f"transcription.provider must be 'openrouter' or 'gemini', got {provider!r}")
    ```
  - `hisab/transcribe.py:11-23` — drop the `openai` branch entirely:
    ```python
    def transcribe(path, cfg):
        path = Path(path)
        tc = cfg["transcription"]
        provider = (tc.get("provider") or "openrouter").lower()
        if provider == "gemini":
            return _gemini(path, os.environ.get("GEMINI_API_KEY", ""), tc.get("gemini_model") or "gemini-2.5-flash")
        base = (tc.get("base_url") or "https://openrouter.ai/api/v1").rstrip("/")
        key_env = tc.get("api_key_env") or "OPENROUTER_API_KEY"
        key = os.environ.get(key_env, "").strip() or cfg["secrets"]["openrouter_key"]
        if not key:
            raise RuntimeError(f"{key_env} is not set")
        return _openai_compatible(path, f"{base}/audio/transcriptions", key, tc.get("model") or "whisper-1", tc.get("language"))
    ```
  - `tests/smoke.py:176-177,299-300` — drop `"agents_sdk": False,` from both inline `model` dicts.
  - `tests/smoke.py:266` — **fix a pre-existing fixture that Phase 1's new check would otherwise
    break**: the runner-tests `runner_cfg` dict sets `"transcription": {"provider": "fake-provider"}`,
    and later in the same block (`written = write_tenant_config(...)`, then `loaded = hisab_load(written)`)
    that dict is written to a tenant config file and loaded through `hisab.config.load` — which
    would now reject `"fake-provider"`. Change it to `"transcription": {"provider": "openrouter"}`;
    the test's purpose (proving `vault_root`/`data_root` path resolution) is unaffected, and every
    later use of the same `runner_cfg` object in that block (reconcile, worker, quota tests) inherits
    the fix since it's one shared dict.
  - `tests/smoke.py` imports (top of file, alongside the existing `from hisab...` imports) — add `from hisab import config as cfgmod` and, inside the `if runner_dir.exists():` block where `runner.tenant_config` is already imported, add `from runner import config as runner_cfgmod`.
  - `tests/smoke.py` — add, near the top of the main `try:` block (before the setup-conversation loop is fine; it's an independent check):
    ```python
    bad_cfg = tmp / "bad-provider.yaml"
    bad_cfg.write_text("transcription:\n  provider: openai\n", encoding="utf-8")
    try:
        cfgmod.load(bad_cfg)
    except SystemExit as e:
        assert "openrouter" in str(e) and "gemini" in str(e), e
    else:
        raise AssertionError("bad transcription provider accepted")
    print("config: rejects unknown transcription provider")
    ```
  - `tests/smoke.py` — add the same check for the runner config loader, inside the `if runner_dir.exists():` block (right after the `"runner: tenant_config ok"` print is a natural spot, since `runner.config` is imported there):
    ```python
    bad_runner_cfg = tmp / "bad-runner-provider.yaml"
    bad_runner_cfg.write_text("transcription:\n  provider: openai\n", encoding="utf-8")
    try:
        runner_cfgmod.load(bad_runner_cfg)
    except SystemExit as e:
        assert "openrouter" in str(e) and "gemini" in str(e), e
    else:
        raise AssertionError("bad runner transcription provider accepted")
    print("runner config: rejects unknown transcription provider")
    ```
  - `config.example.yaml:12-13` — drop the `agents_sdk` line; line 16 comment `# openrouter | openai | gemini (...)` → `# openrouter | gemini`.
  - `.env.example:9-10` — drop `OPENAI_API_KEY=`; reword the comment above `GEMINI_API_KEY=` to `# Only if you use examples/config.gemini.yaml`.
  - `examples/config.openrouter.yaml:14`, `examples/config.gemini.yaml:14` — drop the `agents_sdk` line.
  - `examples/config.openai.yaml` — delete.
  - Gitignored working copies in this worktree (not committed, needed so later phases can actually run): `config.yaml`, `config-dev.yaml`, `runner/config.yaml` — drop their `agents_sdk` lines too, for consistency with the examples they were copied from.
- Test: `python3 tests/smoke.py` — must print `config: rejects unknown transcription provider` and `runner config: rejects unknown transcription provider`, and end `ALL OK`.

### Phase 2 — Runner config per profile, two compose files
**Status:** Done — both compose files validate with `docker compose config -q`; smoke.py still ALL OK; gitignored runner/config.yaml (Gemini) and new runner/config-dev.yaml (OpenRouter) written locally.
- Files:
  - `docker-compose.runner.yml` — replace the header comment (it currently tells the operator to hand-uncomment a `dev` block; that block moves to a new file) and the `runner.volumes`/`environment` entries:
    ```yaml
    # Hosted mode only — separate from docker-compose.yml, which self-host users run unchanged.
    #
    # local profile (Firebase Emulator Suite): `make up` on its own brings up the emulators in the
    # background and starts this file with FIRESTORE_EMULATOR_HOST=host.docker.internal:8080 and
    # GCLOUD_PROJECT=demo-hisab. Neither variable is a secret; they are passed through from the
    # shell, not stored in .env.
    #
    # dev profile (an existing dedicated, non-production Firebase project): `make dev` layers
    # docker-compose.runner.dev.yml on top, which supplies GOOGLE_APPLICATION_CREDENTIALS and the
    # service-account bind mount and clears FIRESTORE_EMULATOR_HOST. Never point either profile at
    # a production project or a payment provider.
    services:
      runner:
        build:
          context: .
          dockerfile: runner/Dockerfile
        env_file: .env                     # RUNNER_PRIVATE_KEY + the model key(s); WHATSAPP_TOKEN there is ignored — each tenant's comes from Firestore
        environment:
          - FIRESTORE_EMULATOR_HOST        # pass-through: set in the shell for the local profile, absent for dev
          - GCLOUD_PROJECT
        volumes:
          - ${RUNNER_CONFIG:-./runner/config.yaml}:/app/runner/config.yaml:ro
          - ./runner-data:/app/runner-data   # vault/<uid>, data/<uid>, tenants/<uid> for every tenant
        extra_hosts:
          - "host.docker.internal:host-gateway"   # Linux hosts; Docker Desktop already resolves it
        restart: unless-stopped
    ```
  - New `docker-compose.runner.dev.yml`:
    ```yaml
    # Dev-profile override for docker-compose.runner.yml — `make dev` layers this on top so the base
    # file's FIRESTORE_EMULATOR_HOST/GCLOUD_PROJECT pass-through (local/emulator profile) is untouched.
    # GOOGLE_APPLICATION_CREDENTIALS and the service-account bind mount exist only when this file is
    # applied. This file deliberately does NOT try to clear FIRESTORE_EMULATOR_HOST with an empty
    # value: google-cloud-firestore's client checks os.getenv("FIRESTORE_EMULATOR_HOST") is not None,
    # so FIRESTORE_EMULATOR_HOST= would still point it at an emulator on host "". `make dev` instead
    # runs docker compose under `env -u FIRESTORE_EMULATOR_HOST`, so the base file's bare
    # `- FIRESTORE_EMULATOR_HOST` pass-through finds nothing and the variable is genuinely absent
    # inside the container, regardless of what the calling shell has exported.
    services:
      runner:
        environment:
          - GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
        volumes:
          - ${RUNNER_SERVICE_ACCOUNT:-./service-account.json}:/app/service-account.json:ro
    ```
  - `runner/config.example.yaml` — rewrite as the Gemini profile:
    ```yaml
    # Copy to runner/config.yaml. Safe to commit; the one secret (RUNNER_PRIVATE_KEY) lives in .env.
    # vault_root/data_root/tenants_dir are resolved to absolute paths at load time RELATIVE TO THIS FILE
    # (runner/), so ../runner-data is the repo-root runner-data/ that docker-compose.runner.yml mounts.
    # This is the Gemini profile `make up` selects by default. For the OpenRouter dev profile see
    # examples/runner-config.openrouter.yaml — copy it to a gitignored runner/config-dev.yaml.

    vault_root: ../runner-data/vault
    data_root: ../runner-data/data
    tenants_dir: ../runner-data/tenants

    ledger:
      template: shop          # personal | shop — used only when a tenant's ledger folder is empty
      currency: PKR

    # Model calls per tenant per month (spec 001, "Revoke, quota, and money"). Every tenant gets this
    # same allowance for now — plan-based tiers are future work. null = unlimited (self-host default).
    quota:
      monthly_limit: 1000

    # Always the runner's own — never tenant-supplied (spec 001, "Tenancy and ledger ownership").
    model:
      id: gemini-3.8-flash
      base_url: https://generativelanguage.googleapis.com/v1beta/openai
      api_key_env: GEMINI_API_KEY
      provider_pin: null

    transcription:
      provider: gemini
      gemini_model: gemini-2.5-flash
    ```
  - New `examples/runner-config.openrouter.yaml`:
    ```yaml
    # OpenRouter profile for runner/config.yaml — used by the dev profile (`make dev`) against the
    # dedicated dev Firebase project. cp examples/runner-config.openrouter.yaml runner/config-dev.yaml
    vault_root: ../runner-data/vault
    data_root: ../runner-data/data
    tenants_dir: ../runner-data/tenants

    ledger:
      template: shop
      currency: PKR

    quota:
      monthly_limit: 1000

    model:
      id: openai/gpt-4.1-mini
      base_url: null           # null = OpenRouter
      api_key_env: null        # null = OPENROUTER_API_KEY
      provider_pin: null

    transcription:
      provider: openrouter
      model: openai/whisper-1
      language: null
    ```
  - Gitignored working copies in this worktree: overwrite `runner/config.yaml` with the Gemini content above; create `runner/config-dev.yaml` with the OpenRouter content above (both needed for Phase 5's `check_endpoint` runs and for the manual `make up`/`make dev` tests).
- Test: `docker compose -f docker-compose.runner.yml config -q` and `docker compose -f docker-compose.runner.yml -f docker-compose.runner.dev.yml config -q` both exit 0; `python3 tests/smoke.py` still `ALL OK` (the runner tests build tenant configs in-process, not through these compose files, so this phase shouldn't touch their behaviour — confirms no regression).

### Phase 3 — Makefile: `make selfhost*`, new `make up`/`dev`/`down`/`down-v`
**Status:** Done — full manual sequence run: `make dev` failed fast naming `./service-account.json`; self-host container up → `make runner-up` refused with the HTTP 409 message → self-host down → `make up` brought up emulators+runner, portal verified reachable at :3031 (curl, contains "hisab") → `make down` cleanly stopped both, pid file removed, ports 3031/9099/8080 free. `python3 tests/smoke.py` ALL OK throughout (a side effect of `make up`'s `npm install` even flipped the JS↔Python sealed-box round trip from skipped to passing).
- Files: `Makefile` (full replacement below), `.gitignore` (add `.emulators.pid` next to the existing `.landing-server.pid`/`.landing-server.log` lines — `firebase-debug.log`/`firestore-debug.log`/`ui-debug.log` are already gitignored, inherited from GH-7's branch this worktree is based on; nothing to add for those, just confirm they're still there).
- Change: replace `Makefile` in full with:
  ```makefile
  .DEFAULT_GOAL := help

  .PHONY: help selfhost selfhost-dev selfhost-down selfhost-down-v selfhost-logs selfhost-restart selfhost-shell up dev down down-v check sample demo stdin check-endpoint bakeoff landing landing-check landing-serve landing-up landing-down rules-test emulators emulators-up emulators-down runner-up runner-logs runner-down runner-down-v

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
  landing: ## Build the Hosted Hisab landing page and portal shell to landing/out. Override: make landing NEXT_PUBLIC_USE_EMULATORS=0 for the dev/remote profile
  	cd landing && npm install && NEXT_PUBLIC_USE_EMULATORS=$(NEXT_PUBLIC_USE_EMULATORS) npm run build

  landing-check: ## Run the landing static checks (three languages, verification direction, no payment collection)
  	python3 tests/check_landing.py

  # ---- hosted mode: local profile (emulators on the host, runner in Docker, portal from landing/out) ----
  # 3031 serves landing/out through the Hosting emulator; auth 9099 and firestore 8080 are in firebase.json.
  FIREBASE_PROJECT ?= demo-hisab
  EMULATORS_PID := .emulators.pid

  up: landing emulators-up runner-up ## Hosted local stack: Gemini runner + Auth/Firestore/Hosting emulators + portal at :3031
  	@echo "OTPs → tail -f firebase-debug.log, or: curl http://localhost:9099/emulator/v1/projects/$(FIREBASE_PROJECT)/verificationCodes"

  down: runner-down emulators-down ## Stop the hosted local stack, keep runner-data/
  down-v: runner-down-v emulators-down ## Stop the hosted local stack AND wipe runner-data/

  dev: NEXT_PUBLIC_USE_EMULATORS := 0
  dev: RUNNER_CONFIG ?= ./runner/config-dev.yaml
  dev: RUNNER_SERVICE_ACCOUNT ?= ./service-account.json
  dev: ## Hosted dev-profile stack: OpenRouter runner against the dev Firebase project, portal built with emulators off
  	@test -f $(RUNNER_SERVICE_ACCOUNT) || { echo "$(RUNNER_SERVICE_ACCOUNT) missing — the dev Firebase project isn't provisioned yet"; exit 1; }
  	@test -f $(RUNNER_CONFIG) || { echo "$(RUNNER_CONFIG) missing — cp examples/runner-config.openrouter.yaml $(RUNNER_CONFIG)"; exit 1; }
  	@grep -q '^RUNNER_PRIVATE_KEY=.\+' .env || { echo "RUNNER_PRIVATE_KEY missing from .env — python3 -m runner.keygen"; exit 1; }
  	$(MAKE) landing NEXT_PUBLIC_USE_EMULATORS=$(NEXT_PUBLIC_USE_EMULATORS)
  	RUNNER_CONFIG=$(RUNNER_CONFIG) RUNNER_SERVICE_ACCOUNT=$(RUNNER_SERVICE_ACCOUNT) env -u FIRESTORE_EMULATOR_HOST docker compose -f docker-compose.runner.yml -f docker-compose.runner.dev.yml up -d --build
  	@echo "runner (dev) → docker compose -f docker-compose.runner.yml -f docker-compose.runner.dev.yml"

  emulators: ## Auth + Firestore + Hosting emulators in the foreground (demo project; OTPs print here). Run `make landing` first
  	@test -d landing/out || { echo "landing/out missing — run 'make landing' first"; exit 1; }
  	firebase emulators:start --only auth,firestore,hosting --project $(FIREBASE_PROJECT)

  emulators-up: ## Auth + Firestore + Hosting emulators in the background (demo project; OTPs land in firebase-debug.log). Run `make landing` first
  	@test -d landing/out || { echo "landing/out missing — run 'make landing' first"; exit 1; }
  	@if [ -f $(EMULATORS_PID) ] && kill -0 `cat $(EMULATORS_PID)` 2>/dev/null; then \
  		echo "emulators already running (pid `cat $(EMULATORS_PID)`)"; \
  	elif lsof -ti :3031 >/dev/null 2>&1; then \
  		echo "port 3031 is in use by something else"; exit 1; \
  	else \
  		nohup firebase emulators:start --only auth,firestore,hosting --project $(FIREBASE_PROJECT) >firebase-debug.log 2>&1 & echo $$! >$(EMULATORS_PID); \
  		sleep 2; \
  	fi

  emulators-down: ## Stop the background emulators
  	@if [ -f $(EMULATORS_PID) ]; then kill `cat $(EMULATORS_PID)` 2>/dev/null; rm -f $(EMULATORS_PID); echo "emulators stopped"; else echo "emulators not running"; fi

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

  runner-down-v: ## Stop the runner AND delete runner-data/ (every tenant's ledger, state and per-tenant config)
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
  ```
  Note the two-space indentation above is this document's fence; the actual file uses tabs for every
  recipe line, matching the existing Makefile — `/implement` must write real tabs, not spaces, or
  `make` will reject the target with "missing separator".
- Test: `python3 tests/smoke.py` unaffected (Makefile isn't exercised by it) — run for regression only. Then the manual sequence: `make selfhost` (expect worker up, `docker compose -f docker-compose.yml ps` shows it running) → `make up` (expect it to refuse, naming HTTP 409 and `make selfhost-down`) → `make selfhost-down` → `make up` (expect emulators + runner up, portal reachable at `http://localhost:3031/portal/`) → `make down` (expect both stopped, `runner-data/` intact) → `make dev` (expect immediate exit 1 naming `service-account.json`, since it doesn't exist in this worktree).

### Phase 4 — Docs
**Status:** Done — README.md, AGENTS.md, runner/README.md, landing/README.md all updated and read back; README's Hosted Hisab paragraph kept short per the lead's parallel GH-5 edits. smoke.py still ALL OK.
- Files:
  - `README.md:60` — `4. \`docker compose up -d\`` → `4. \`docker compose up -d\` (or \`make selfhost\`)`.
  - `README.md:67-71` (the "Hosted Hisab" section) — replace with:
    ```markdown
    ## Hosted Hisab (in progress)

    For people who will never run Docker: sign in with a phone number, paste your agent's key, send the code the portal shows you to your agent, and we run the worker. Your key and ledger then live on our server, encrypted. Send `export-ledger` to your agent and the ledger comes back as a ZIP; revoke stops the worker and deletes the key. Self-host (above, `make selfhost`) keeps both on your own machine. 300 PKR/month is the presentation price; nothing in this repo collects it.

    What exists today: `make up` runs the whole local hosted stack — the Auth/Firestore/Hosting emulators, the runner on Gemini, and the portal at http://localhost:3031/portal/ — as one command; `make dev` runs the runner on OpenRouter against the dedicated dev Firebase project once it exists. `make landing` builds the portal alone. Design: [`docs/brainstorm/hosted-portal.md`](docs/brainstorm/hosted-portal.md); spec: [`docs/specs/001-hosted-portal.md`](docs/specs/001-hosted-portal.md).
    ```
    Kept deliberately short — the lead's parallel GH-5 branch rewrites the rest of this section's
    detail (which issues are open, the runner/export-ledger description) in the same paragraph, so a
    short replacement here keeps whichever branch merges second a clean rebase, not a conflict.
  - `AGENTS.md:66` (Commands table, "Container" row) — append `(or \`make selfhost\`)` after the `docker compose` commands.
  - `AGENTS.md:68` (Commands table, "Hosted mode, the full local loop" row) — replace the one row with two:
    ```markdown
    | Hosted mode, the full local loop (Gemini + emulators + runner + portal at :3031) | `make up` (then `make down` / `make down-v`) — see runner/README.md |
    | Hosted mode, the dev profile (OpenRouter + the dedicated dev Firebase project) | `make dev` — fails fast until the project is provisioned |
    ```
  - `runner/README.md` — replace the "One-time setup" section's nothing (unchanged), and replace the "The full local loop" section (currently the four-row table plus the closing line) with:
    ```markdown
    ## The full local loop

    One command from the repo root: `make up` builds the portal, brings up the Auth/Firestore/Hosting
    emulators in the background (`make emulators` is the foreground variant), and starts the runner on
    the Gemini profile (`runner/config.yaml`). `make down` stops all of it, keeping `runner-data/`;
    `make down-v` also wipes it. Lower-level pieces stay available: `make landing` (build only),
    `make emulators` (foreground), `make runner-up` / `runner-logs` / `runner-down` / `runner-down-v`
    (the runner alone, on `RUNNER_CONFIG`, default `./runner/config.yaml`).

    | Step | What |
    |---|---|
    | `make up` | portal built, emulators up in the background, runner up on Gemini |
    | http://localhost:3031/portal/ | sign in with any number (the emulator never sends SMS), paste a **demo** agent's key, send `verify <nonce>` from the phone that created that agent |
    | OTPs | `tail -f firebase-debug.log`, or `curl http://localhost:9099/emulator/v1/projects/demo-hisab/verificationCodes` |
    | `make down` / `make down-v` | stop the stack, optionally wiping `runner-data/` |

    The dev profile (`make dev`) runs the runner on OpenRouter (`RUNNER_CONFIG=./runner/config-dev.yaml`)
    against the dedicated dev Firebase project instead of the emulators — see the profile table below.
    It fails fast with one line if the service-account JSON isn't there yet; the project doesn't exist
    as of this writing, so `make dev` is wiring and docs only until it does.

    Then `make rules-test` for the rules as an attacker, `python3 tests/smoke.py` for everything else.
    ```
  - `runner/README.md` — the "Two profiles" table's `Command` column: `local` row → `` `make up` ``; `dev` row → `` `make dev` `` and its `Credentials` cell → `a gitignored service-account JSON, mounted by \`docker-compose.runner.dev.yml\``.
  - `landing/README.md`'s command table — replace with:
    ```markdown
    | Command | What |
    |---|---|
    | `make landing` | `npm install && npm run build` — writes the static export to `landing/out/`. `NEXT_PUBLIC_USE_EMULATORS=0` for the dev/remote profile |
    | `make landing-check` | Runs `tests/check_landing.py` — three-language completeness, verification direction, no payment collection, `firebase.json` shape, a portal string per runner `lastError` code |
    | `make emulators` | Serves `landing/out` at http://localhost:3031 through the Hosting emulator, with Auth and Firestore beside it (foreground; `make up` is the background hosted stack) |
    | `make up` | The whole hosted local stack: emulators in the background, the runner on Gemini, the portal at http://localhost:3031/portal/ |
    | `make dev` | The runner on OpenRouter against the dedicated dev Firebase project, portal built with emulators off |
    | `make selfhost` | Runs the self-host worker and serves `landing/out` at `http://localhost:3030` (no Firebase; the portal will not sign in) |
    ```
- Test: read all four files back; `python3 tests/smoke.py` (regression only — `check_landing.py` doesn't read these prose sections).

### Phase 5 — Full-repo validation
**Status:** Done, with one external caveat — grep clean, `config.openai.yaml` gone, both compose
profiles validate, landing builds in both modes, `check_endpoint.py --config runner/config.yaml`
(Gemini) is ALL PASS, `python3 tests/smoke.py` ALL OK. `check_endpoint.py --config runner/config-dev.yaml`
(OpenRouter) fails on live calls with `HTTP 401 API key expired` — reproduced the same failure
against the pre-existing, untouched root `config-dev.yaml`, so this is the sponsor `OPENROUTER_API_KEY`
in `.env` having expired, not a wiring bug: the key-presence and model-listing/tools-support checks
against OpenRouter both pass, proving the config file and its OpenRouter profile load and resolve
correctly. Flagged to the lead rather than worked around.
- Files: none (verification only).
- Change: none.
- Test, run in order:
  1. `grep -rniE 'provider == "openai"|OPENAI_API_KEY|agents_sdk|config\.openai' hisab runner tests examples config.example.yaml .env.example` — expect no output, exit 1.
  2. `test ! -f examples/config.openai.yaml` — expect exit 0.
  3. `docker compose -f docker-compose.runner.yml config -q && docker compose -f docker-compose.runner.yml -f docker-compose.runner.dev.yml config -q` — expect exit 0.
  4. `cd landing && NEXT_PUBLIC_USE_EMULATORS=1 npm run build && NEXT_PUBLIC_USE_EMULATORS=0 npm run build` — both succeed.
  5. `python3 tests/check_endpoint.py --config runner/config.yaml` (Gemini, needs `GEMINI_API_KEY` in `.env`) and `python3 tests/check_endpoint.py --config runner/config-dev.yaml` (OpenRouter, needs `OPENROUTER_API_KEY` in `.env`) — both `ALL PASS`.
  6. `python3 tests/smoke.py` — `ALL OK`.

## Risks

- Killing `emulators-up`'s background PID may not terminate every child process the Firebase CLI
  spawns (a known Firebase CLI quirk — it forks a Java process for Firestore). If `make down`/
  `emulators-down` leaves something on port 8080/9099/3031, `pkill -f firebase` is the manual
  fallback; not automated here since `landing-up`'s existing pid-file pattern has the same property
  and this plan only mirrors it.
- `make dev` cannot be verified end-to-end until the dev Firebase project and its service-account
  JSON exist. Everything short of that (compose syntax, the landing build, the fail-fast message) is
  covered; the actual connect-a-tenant flow on the dev profile is the owner's manual step later, as
  issue #21 itself says.
- The `runner-up` self-host collision guard checks `docker compose -f docker-compose.yml ps`; it
  does not catch a bare `python -m hisab.loop --stdin` or a self-host container started under a
  different compose project name polling the same WhatsApp token. This matches the literal decision
  in issue #21 (guard against the self-host *container*) and the existing "one container per token"
  discipline already documented in `AGENTS.md`, not a new gap this plan introduces.

## Out of scope

- Provisioning the dev Firebase project or generating its service-account JSON — the owner's manual
  follow-up, referenced but not performed here.
- Deploying the portal to real Firebase Hosting for the dev profile — only the build (`landing/out`)
  is wired; where it's served once the project exists is a separate concern.
- Issues #5 (revoke), #6 (quota UI) and #7's remaining open edges — untouched by this plan.
