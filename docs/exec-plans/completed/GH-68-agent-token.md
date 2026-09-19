---
slug: GH-68-agent-token
issue: 68
status: completed
open_questions: none
---

# feat: read the WhatsApp token from WHATSAPP_AGENT_TOKEN, WHATSAPP_TOKEN as fallback          ✅ COMPLETED — 2026-09-20

## Problem
Hisab reads its WhatsApp token from `WHATSAPP_TOKEN`; wa-agent, which it runs on, uses `WHATSAPP_AGENT_TOKEN` (`wa_agent/state.py:15`). One `.env` should serve both. Owner's decision ([#68](https://github.com/mhmzdev/hisab-whatsapp/issues/68)): the new name wins, the old one still works with a one-line stderr note to rename it, and every user-facing doc switches to the new name.

The dangerous part is the hosted runner. `runner/reconcile.py:27-30` builds each worker's env from the runner's own `os.environ` and sets the tenant token as `WHATSAPP_TOKEN`; `runner/main.py:49` has already `load_dotenv()`-ed the operator's `.env` into that environ. Once the worker prefers `WHATSAPP_AGENT_TOKEN`, an operator `.env` that sets it would make **every tenant poll with the operator's token**.

## Approach
One resolver, in `hisab/config.py`, owns both names; the runner imports the names from it so the two sides cannot drift.

**Worker** (`hisab/config.py`): module constants `TOKEN_ENV = "WHATSAPP_AGENT_TOKEN"` and `LEGACY_TOKEN_ENV = "WHATSAPP_TOKEN"`, and `whatsapp_token(env=None)`:
- `env[TOKEN_ENV].strip()` non-empty → return it (silently, even if the old name is also set).
- else (the new name unset, empty or whitespace-only, e.g. `WHATSAPP_AGENT_TOKEN=` left over from `cp .env.example .env`) `env[LEGACY_TOKEN_ENV].strip()` non-empty → return it, and the first time in the process print one stderr line: `config: WHATSAPP_TOKEN is the old name; rename it to WHATSAPP_AGENT_TOKEN in .env`. Never the value. A module flag `_legacy_noted` makes it once per process.
- else `""`.
`load()` (`hisab/config.py:59`) calls `whatsapp_token()`. `hisab/loop.py:168` says `WHATSAPP_AGENT_TOKEN is empty; put it in .env`. This is an operator stderr exit, not a user reply, so no `errors.py` code.

**Runner** (`runner/reconcile.py`), four changes:
1. `_tenant_env` drops **both** token names from the inherited environ (a new `OPERATOR_TOKEN_ENV_KEYS = {TOKEN_ENV, LEGACY_TOKEN_ENV}`, kept apart from `RUNNER_ONLY_ENV_KEYS` with its own comment: the operator's token, under either name, never reaches a tenant).
2. It sets the tenant token as `env[TOKEN_ENV]`.
3. `state_hash` reads `env.get(TOKEN_ENV)`. The payload key stays `"token"`, so a running tenant's hash is unchanged by the upgrade.
4. `_tenant_env` sets `env[NO_DOTENV_ENV] = "1"` (`NO_DOTENV_ENV = "HISAB_NO_DOTENV"`, a constant in `hisab/config.py`). `hisab/loop.py` gets `load_env()`, which calls `cfgmod.load_dotenv()` only when that marker is unset, and `main()` (`:330`) calls it.

Why 4 (lead's addition): the worker, started by `runner/workers.py:24` in the runner's cwd, used to run `load_dotenv()` (`hisab/loop.py:330`) against that cwd's `.env`. In Docker there is no `/app/.env` (both Dockerfiles `COPY` specific folders), but a runner started from the repo root would hand every tenant the operator's `.env`, setdefault-ing back `RUNNER_PRIVATE_KEY` (the secret `RUNNER_ONLY_ENV_KEYS` strips) and a legacy token. A tenant worker now gets its whole environment from the runner, and nothing from a file. Self-host (no marker) loads `.env` as today; `runner/main.py:49`'s own `load_dotenv()` is untouched.

Nothing else in the runner reads the name. Checked: `grep -rn WHATSAPP runner/` hits only `reconcile.py` and the `crypto.py` docstring. `runner/config.py:49` reads only `RUNNER_PRIVATE_KEY`, and `workers.py` passes `env` through unchanged. `hisab/wa.py:86` takes the token as an argument and never reads wa-agent's env lookup. `tests/check_endpoint.py` doesn't name the variable, so it's unchanged.

Invariants kept: six tools, no new user-facing string (the note and the exit are operator stderr), no secret value printed, transport untouched.

## Success criteria
- [x] Only `WHATSAPP_AGENT_TOKEN` set → `load()` returns it, no stderr note — `verify: python3 tests/smoke.py`
- [x] Only `WHATSAPP_TOKEN` set → `load()` returns it, the rename note printed exactly once across two loads, note names both variables and never contains the value — `verify: python3 tests/smoke.py`
- [x] Both set → the new one wins, no note — `verify: python3 tests/smoke.py`
- [x] New name empty (`WHATSAPP_AGENT_TOKEN=`) or whitespace-only with the old one set → the old one is used, with the rename note — `verify: python3 tests/smoke.py`
- [x] Hosted: with the runner's environ setting BOTH names to operator values, the tenant worker's env has `WHATSAPP_AGENT_TOKEN` = the tenant's decrypted token, no `WHATSAPP_TOKEN`, `whatsapp_token(worker_env)` = tenant token, and the env carries `HISAB_NO_DOTENV=1` — `verify: python3 tests/smoke.py`
- [x] A tenant worker never reads `.env`: in a temp cwd whose `.env` sets `RUNNER_PRIVATE_KEY` and `WHATSAPP_TOKEN`, `load_env()` under the runner's marker loads neither, and without the marker (self-host) loads both as today — `verify: python3 tests/smoke.py`
- [x] `state_hash` follows the tenant token: two tenant tokens → two hashes; the operator's environ does not change a tenant's hash — `verify: python3 tests/smoke.py`
- [x] No user-facing doc tells anyone to set `WHATSAPP_TOKEN`: every remaining mention in docs, `.env.example` and compose comments sits on a line that also names `WHATSAPP_AGENT_TOKEN` — `verify: ! git grep -n WHATSAPP_TOKEN -- '*.md' '*.yml' .env.example ':!docs/exec-plans' ':!docs/feat-checklist' | grep -v WHATSAPP_AGENT_TOKEN`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases
### Phase 1 — worker reads both names
**Status:** Done — `whatsapp_token()` in config.py, loop.py's exit names `TOKEN_ENV`, smoke covers new / old / both / empty / whitespace / none
- Files: `hisab/config.py` (constants + `whatsapp_token` near the top; `:59` in `load()`; add `import sys`), `hisab/loop.py:168`, `tests/smoke.py` (config section, after the timezone checks near `:476`).
- Change: as in Approach.
- Test: a small `_token_env(**vals)` context manager in smoke that saves both names from `os.environ`, sets or clears them, and restores them afterwards (the shell may export real keys). Cases: only new; only old (reset `cfgmod._legacy_noted = False`, capture stderr with `contextlib.redirect_stderr`, load twice, assert one note naming both variables and not containing the value); both (new wins, no note); new `""` and new `"  "` with old set (old used, note printed, each with `_legacy_noted` reset). `load()` is called on `tmp / "no-such-config.yaml"`.

### Phase 2 — the runner hands each tenant its own token
**Status:** Done — `_tenant_env` strips both names and sets the tenant's as `TOKEN_ENV` plus `HISAB_NO_DOTENV=1`, `state_hash` reads `TOKEN_ENV`, `loop.load_env()` skips `.env` under the marker; smoke proves each, and three mutations (no strip, old name, always load) each fail it
- Files: `runner/reconcile.py:22-40`, `hisab/config.py` (`NO_DOTENV_ENV`), `hisab/loop.py` (`load_env()`, `main()` at `:330`), `tests/smoke.py` (the reconcile block, `:1043-1072`).
- Change: as in Approach, changes 1–4. `from hisab.config import LEGACY_TOKEN_ENV, NO_DOTENV_ENV, TOKEN_ENV`.
- Test: in the existing reconcile block, also set `os.environ["WHATSAPP_AGENT_TOKEN"] = "operator-new"` and `os.environ["WHATSAPP_TOKEN"] = "operator-old"`, and restore both in the `finally`. After the first reconcile, assert:
  - `last_env["WHATSAPP_AGENT_TOKEN"] == "fake-wa-token"` and `"WHATSAPP_TOKEN" not in last_env`
  - `cfgmod.whatsapp_token(last_env) == "fake-wa-token"`
  - `last_env["HISAB_NO_DOTENV"] == "1"`
  - the `.env` test: `chdir` into a temp dir whose `.env` sets `RUNNER_PRIVATE_KEY=op-key` and `WHATSAPP_TOKEN=op-tok`, both absent from `os.environ`. With `HISAB_NO_DOTENV=1`, `loop.load_env()` leaves both absent. With the marker unset, it loads both. Restore the cwd and environ in a `finally`.
  - hash: `state_hash(_tenant_env("a"), cfg) != state_hash(_tenant_env("b"), cfg)`, and `state_hash(_tenant_env("a"), cfg)` is the same with and without the operator names in `os.environ`.
  - the existing idempotency assertion (`launcher.calls == 1`) still holds.

### Phase 3 — docs and comments to the new name
**Status:** Done — every listed doc and comment switched; runner/README gains the handoff paragraph; smoke.py:124's export fixture carries both names; docs check exits 0
- `.env.example:4` → `WHATSAPP_AGENT_TOKEN=`, with the comment gaining "(WHATSAPP_TOKEN, the old name, still works)".
- `README.md:102` → "paste the WhatsApp key into `WHATSAPP_AGENT_TOKEN` and your model key …".
- `runner/README.md:44` → `` `WHATSAPP_AGENT_TOKEN`/`OPENROUTER_API_KEY` ``, plus one sentence under it: the runner strips both WhatsApp token names from its own environment and hands each worker only its tenant's token as `WHATSAPP_AGENT_TOKEN`.
- `runner/crypto.py:5` docstring → `WHATSAPP_AGENT_TOKEN/OPENROUTER_API_KEY`.
- `docker-compose.runner.yml:18` comment → "a WhatsApp token there (either name) never reaches a tenant — each tenant's comes from Firestore".
- `docs/self-host-vps.md` step 4 → fill in `WHATSAPP_AGENT_TOKEN`, with the grep `grep -cE '^(WHATSAPP_AGENT_TOKEN|WHATSAPP_TOKEN|OPENROUTER_API_KEY|GEMINI_API_KEY)=.+' .env`. The old name stays in the pattern so a server with an existing `.env` still counts, and "2 or more" still holds. Step 7 → "If it says WHATSAPP_AGENT_TOKEN is empty".
- `AGENTS.md` repo map, the `config.py` line → "config.yaml + .env (secrets only from the environment; the WhatsApp token from WHATSAPP_AGENT_TOKEN, WHATSAPP_TOKEN as the old-name fallback)".
- `ARCHITECTURE.md` hosted section, `:137` paragraph → one sentence: the runner hands each worker only its tenant's token as `WHATSAPP_AGENT_TOKEN`, strips the operator's (either name) and `RUNNER_PRIVATE_KEY`, and marks the worker `HISAB_NO_DOTENV` so it never reads a `.env`.
- Test: the `git grep` criterion above, plus smoke.

## Risks
- **Operator token or runner key leaking to tenants.** Covered by Phase 2's assertions on the tenant env and by the `HISAB_NO_DOTENV` `.env` test.
- **Someone sets `HISAB_NO_DOTENV` on a self-host box.** `.env` is then ignored and the token must come from the real environment. The name says so, and nothing documents it for self-host.
- **A self-host `.env` with a stale `WHATSAPP_AGENT_TOKEN` and a fresh `WHATSAPP_TOKEN`** will now use the stale one. This follows from the owner's "new wins" decision. The rename note only prints when the old name is actually used.
- **Smoke inheriting real keys from the shell.** The context manager saves and restores both names. Manual runs use `env -i`.

## Out of scope
- `tests/check_endpoint.py`: it never reads the WhatsApp token.
- Historical `docs/exec-plans/`, `docs/feat-checklist/`, `docs/brainstorm/` and `docs/specs/`.
- Removing the `WHATSAPP_TOKEN` fallback. That needs a later issue once servers have renamed.
