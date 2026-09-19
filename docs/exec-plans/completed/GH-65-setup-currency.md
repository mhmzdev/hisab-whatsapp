---
slug: GH-65-setup-currency
issue: 65
status: completed
open_questions: none
---

# fix: the currency chosen in setup survives a restart          ✅ COMPLETED — 2026-09-20

## Problem
[#65](https://github.com/mhmzdev/hisab-whatsapp/issues/65). Setup writes the chosen currency to `settings.json` (`hisab/setup.py:142`) and sets it on the live ledger (`hisab/setup.py:94`). Nothing reads it back: every restart builds `Ledger(cfg["ledger"]["path"], cfg["ledger"]["currency"], tz)` (`hisab/loop.py:41`), so the system prompt's default currency (`hisab/agent.py:51`), `fmt_amount`'s default (`hisab/ledger.py:96`) and the report's `-X` conversion (`hisab/ledger.py:236`) fall back to config.yaml's value, PKR by default. The user is not told.

The rule (issue, owner): once setup has written `settings.json`, its currency wins over config.yaml; config.yaml is the default for a ledger with no settings yet (before and during setup).

## Approach
The precedence lives **inside `Ledger`**, so every construction path gets it: self-host (`hisab/loop.py:41`), hosted tenants (the same line, fed by `runner/tenant_config.py:19`, which passes the runner's `ledger.currency`, PKR by default) and `--stdin`.

`hisab/ledger.py`:
- `__init__` keeps its signature; `self.currency = currency` (`:28`) becomes `self.default_currency = currency` with a short comment (config.yaml's, used until setup writes `settings.json`, #65).
- `currency` becomes a read-only property:
  ```python
  CURRENCY_RE = re.compile(r"[A-Z]{3,4}")  # the shape setup accepts (hisab/setup.py:74-76)

  @property
  def currency(self):
      """setup's answer from settings.json once written; config.yaml's default before setup, or if it is missing or malformed (#65)."""
      cur = self.settings().get("currency")
      return cur if isinstance(cur, str) and CURRENCY_RE.fullmatch(cur) else self.default_currency
  ```
  Read on every access, so the value never goes stale: setup's `set_settings` (`setup.py:142`) is what switches a live ledger over, and a restart reads the same file. The cost is one small JSON read per access (`system()` already reads `settings.json` through `language()`).
- `settings()` (`:51-56`) also never crashes on a file that parses but is not an object (`[]`, `"x"`) or is not UTF-8: catch `ValueError` (covers `JSONDecodeError` and `UnicodeDecodeError`) and return `{}` unless the result is a `dict`. That is the "invalid settings.json falls back, never crashes" half; `language()` and `set_settings` benefit too.

`hisab/setup.py:94`: drop `self.ledger.currency = cur` (the property has no setter, and `settings.json` is now the source). `cur` stays a local; `write()` already uses it for `hisab.md`'s commodity line and the periodic rules, and writes it to `settings.json` at `:142` before `quarter_file`/`check`.

Nothing caches the old value: `Agent.system()` (`agent.py:48-52`) renders the prompt per message from `self.ledger.currency`; `Tools` reads `ledger` per call; `hisab/loop.py:41` is the only place that reads `cfg["ledger"]["currency"]`. `/lang` (`loop.py:73`) and every other writer go through `set_settings`, which merges (`ledger.py:58-62`), so the currency is kept.

`sample-vault/` is unaffected: its setup answers PKR (`tests/make_sample.py:17`), and config's default is PKR, so no regeneration.

Docs:
- `docs/self-host-vps.md` step 5 drops the currency question and the `ledger: currency:` edit; it keeps the timezone part and tells the user setup in WhatsApp asks for the currency and the code given there is the one Hisab keeps.
- `config.example.yaml:6` and `runner/config.example.yaml:15` get a trailing comment on `currency:`: the default until setup; setup's answer wins after.

Invariants kept: six tools, strict check, entry numbering, transport, no new user-facing string.

## Success criteria
- [x] Self-host restart: setup through `Hisab` with config currency PKR and answer `usd`, then a new `Hisab(cfg)` on the same folders → `ledger.currency == "USD"` and `agent.system()` says `Default currency USD` — `verify: python3 tests/smoke.py`
- [x] Hosted restart: the same through `build_tenant_config` → `write_tenant_config` → `hisab.config.load` (runner currency PKR) → two `Hisab` instances → `USD` — `verify: python3 tests/smoke.py`
- [x] Before setup (no `settings.json`) the ledger's currency is config's (a non-PKR config value, e.g. `EUR`, shows through) — `verify: python3 tests/smoke.py`
- [x] `settings.json` with the currency missing, `""`, `"usd"`, `42`, `"US$"`, malformed JSON, or a JSON list → config's currency, no exception; `language()` still returns `en` — `verify: python3 tests/smoke.py`
- [x] `/lang ur` after setup keeps `USD` in `settings.json` and on the ledger — `verify: python3 tests/smoke.py`
- [x] The report's `-X` follows the setup currency: `_bal` (`ledger.py:235-236`, behind every report) on the USD ledger passes `-X USD` (asserted on the recorded hledger args) — `verify: python3 tests/smoke.py`
- [x] The VPS guide no longer asks for a currency in config.yaml — `verify: ! grep -n "ledger: currency" docs/self-host-vps.md`
- [x] Sample ledger still strict — `verify: hledger -f sample-vault/hisab.md check --strict`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases
### Phase 1 — Ledger resolves the currency; smoke proves restart, hosted and fallbacks
**Status:** Done — `Ledger.currency` is a read-only property over `settings.json` with `default_currency` from config; `settings()` returns `{}` for non-dict or non-UTF-8 files; setup.py:94 dropped; smoke's `_currency_restart` runs self-host and hosted (a separate tenant uid), plus `-X`, `/lang`, the EUR default and nine bad bodies; two mutations (property ignores settings, no dict check) each fail it
- Files: `hisab/ledger.py` (`:22-28`, `:51-56`, `CURRENCY_RE` near the top), `hisab/setup.py:94`, `tests/smoke.py` (a new block after the #28 hosted-setup block, `:103`; the hosted case inside the runner block after `print("runner: tenant_config ok")`, `:951`).
- Change: as in Approach.
- Test:
  - Self-host: a `make_app`-style cfg (currency `PKR`, fake model key, `pending: False`) on fresh temp dirs; `app.ledger.currency == "PKR"` before setup; drive `app.setup.start()` then `app.setup.answer(...)` with `personal, usd, cash, none, none, no, no`; `app2 = Hisab(cfg)`: `app2.ledger.currency == "USD"`, `"Default currency USD" in app2.agent.system()`; `app2.handle("/lang ur")` then `app2.ledger.settings()["currency"] == "USD"` and `Hisab(cfg).ledger.currency == "USD"`.
  - Report `-X`: wrap `app2.ledger.hledger` to record its args (then call through), run `app2.ledger._bal("^assets")`, assert the arg after `"-X"` is `"USD"`.
  - Default shows through: `Ledger(tmp / "cur-eur", "EUR").currency == "EUR"`.
  - Fallbacks: for each bad `settings.json` body (`{"language": "en"}`, `{"currency": ""}`, `{"currency": "usd"}`, `{"currency": 42}`, `{"currency": "US$"}`, `{not json`, `[]`), write it raw and assert `Ledger(dir, "EUR").currency == "EUR"` and `.language() == "en"`.
  - Hosted: `hcfg = dict(loaded, pending=False)` with `hcfg["secrets"] = dict(loaded["secrets"], openrouter_key="fake-not-used")`; `Hisab(hcfg)`, run setup answering `usd` as above; a second `Hisab(hcfg)` has `ledger.currency == "USD"`.

### Phase 2 — docs
**Status:** Done — VPS step 5 asks only the timezone and says setup's currency is the one kept; both config examples comment `currency:` as the pre-setup default; grep criterion exits 0
- Files: `docs/self-host-vps.md:25`, `config.example.yaml:6`, `runner/config.example.yaml:15`.
- Change: step 5 becomes: "ASK my timezone as an IANA name (for example Asia/Karachi). Set timezone: in config.yaml. Leave everything else at its default. The server clock is usually UTC and can stay UTC, because Hisab reads its dates only from timezone in config.yaml. Tell me that setup in WhatsApp asks for my currency code, and the one I give there is the one Hisab keeps." Config comments: `currency: PKR            # the default until setup; the currency answered in setup wins after` (the runner's: "until a tenant's setup").
- Test: the `grep` criterion, plus smoke.

## Risks
- **A hand-edited `settings.json` with a lowercase or odd code** silently falls back to config's currency. Setup never writes such a value (it uppercases and length-checks), so only a hand edit hits this; falling back beats crashing or feeding hledger a bad `-X`.
- **An existing ledger whose `settings.json` currency differs from its config.yaml** (a user who hit this bug and then answered, say, USD in setup) switches to the setup answer on upgrade. That is the fix.
- **Smoke inheriting real keys from the shell:** the new block uses a fake key in cfg and never calls the model. Manual runs use `env -i`.

## Out of scope
- A way to change the currency after setup (a command or tool). Today it takes `/setup` or a hand edit of `settings.json`.
- Multi-currency per tenant.
- Changing `runner/tenant_config.py`: it keeps passing the runner's default, which now only matters before setup.
