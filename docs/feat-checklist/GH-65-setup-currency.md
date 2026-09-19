# GH-65-setup-currency — acceptance checklist   (9 proven · 1 manual · 0 failing)

Scope: 8 files against `main` — `hisab/ledger.py`, `hisab/setup.py`, `tests/smoke.py`, `docs/self-host-vps.md`, `config.example.yaml`, `runner/config.example.yaml`, the plan and the exec-plans INDEX. Intent: [#65](https://github.com/mhmzdev/hisab-whatsapp/issues/65) and `docs/exec-plans/completed/GH-65-setup-currency.md`.

- [x] Self-host restart keeps setup's currency: setup answers `usd` on a PKR config, a new `Hisab(cfg)` reads `USD` and its system prompt says `Default currency USD` — `python3 tests/smoke.py` passes (test: `_currency_restart`, line "currency: setup's answer survives a restart …")
- [x] Hosted restart keeps it: `build_tenant_config` → `write_tenant_config` → `hisab.config.load` (runner currency PKR) → two `Hisab` instances → `USD` — `python3 tests/smoke.py` passes (line "runner: a tenant's setup currency survives a worker restart")
- [x] Before setup, config's currency shows through (`Ledger(dir, "EUR").currency == "EUR"`) — `python3 tests/smoke.py` passes
- [x] A missing or malformed `settings.json` currency falls back to config and never crashes: no key, `""`, `"usd"`, `42`, `"US$"`, truncated JSON, `[]`, a bare string, non-UTF-8 bytes; `language()` stays `en` — `python3 tests/smoke.py` passes
- [x] `/lang ur` after setup keeps `USD` in `settings.json` and on a restarted ledger — `python3 tests/smoke.py` passes
- [x] Reports convert to the setup currency: `_bal` passes `-X USD` — `python3 tests/smoke.py` passes (recorded hledger args)
- [x] The VPS guide no longer asks for a currency in config.yaml — `! grep -n "ledger: currency" docs/self-host-vps.md` exits 0
- [x] Sample ledger unaffected — `hledger -f sample-vault/hisab.md check --strict` ok; `tests/make_sample.py` run on branch and on `main` (scratch copies) gives byte-identical `sample-vault/`, so no regeneration
- [x] Repo check passes — `env -i PATH=… HOME=… python3.11 tests/smoke.py` → `ALL OK` (no inherited keys)
- [?] A real container keeps a non-PKR setup currency across a restart (post-merge, demo agent, per the live-test convention): 1. `HISAB_VAULT=<empty scratch folder> docker compose up -d --build`. 2. From the phone, run setup and answer `USD` to the currency question. 3. Send `500 coffee` and note the reply shows `USD 500.00`. 4. `docker compose restart`. 5. Send `200 lunch` and ask "how much did I spend this month?". Expect `USD` amounts in both replies, and no `PKR`

## Conventions
- Surface: six tools unchanged; no new file or network access.
- Writes: no change to `append`, the strict check or entry numbering; `set_settings` still merges.
- Transport: untouched.
- Language: no new user-facing string.
- Dashboard conventions: commodities still alphabetic, since the property only returns an `[A-Z]{3,4}` code or config's value.
- Privacy: the diff adds no personal path, token or number (`fake-not-used` is the existing smoke placeholder); `.env`, `config.yaml` and `vault/` untouched.
- Tests: every changed unit is exercised in smoke; two mutations (the property ignores `settings.json`; `settings()` without the dict check) each fail it.
- Docs: `config.example.yaml` and `runner/config.example.yaml` say `currency:` is the pre-setup default. ARCHITECTURE.md's `settings.json (language, mode, currency)` is still true. README says nothing about the currency's source.

## Findings
FINDING-01 · Minor · hisab/ledger.py:53-59 — `set_settings` on a `settings.json` that is not an object (e.g. `[]`) now starts from `{}` and overwrites it, where it used to crash. Only a hand edit produces such a file, and overwriting it with valid settings beats a crash on `/lang`. No action proposed.
