---
slug: GH-36-export-ledger-delivery
issue: 36
status: completed
open_questions: none
---

# fix: export-ledger delivers the ZIP — generic-binary upload, local-time name, short caption          ✅ COMPLETED — 2026-09-14

## Problem

[#36](https://github.com/mhmzdev/hisab-whatsapp/issues/36): `export-ledger` never delivers. `WhatsApp.send_document` (`hisab/wa.py:166-184`) uploads the bundle as `application/zip`. The Agent Platform refuses that type with `400 / 131053 "application/zip is not a supported media type"`, so every export ends in `err_export_failed`, whose "send export-ledger again in a bit" can't help.

Decided on 2026-09-14 with the owner, after a live probe:
- **Keep the ZIP; declare it a generic binary.** The platform manual (`docs/agent_guide.pdf`, `POST /agent/v1/media` → "Accepted media types") accepts `application/octet-stream` "for a generic binary file", up to 16 MB, declared in the `type` form field. The probe uploaded a real export that way (200), sent it as a `document` (200), and the owner downloaded and unzipped it on the phone: all canonical files present.
- **File name:** `hisab-2026-09-14-1110.zip`, local date plus hour and minute.
- **Clock:** Asia/Karachi. Today the name uses the container clock (`hisab/loop.py:120`), which is UTC in both images.
- **Caption:** short and in the user's language: `Ledger backup · 14 Sep 2026, 11:10` / `کھاتے کا بیک اپ · 14 Sep 2026، 11:10`.

## Approach

- **Transport.** `send_document(to, path, filename, caption=None, mime="application/octet-stream")` sends `mime` both as the file part's content type and in the `type` form field, as the manual's request syntax shows. The docstring cites the manual's accepted-types rule. A `400` with `error.code 131053` on upload raises `HisabError("export_rejected", …)`, because a refused type or size never succeeds on retry. Any other non-2xx stays a `RuntimeError`, which the loop's `default="export_failed"` classifies as retryable.
- **Clock.** A new top-level config key `timezone` (default `"Asia/Karachi"`) lives in `hisab/config.py` `DEFAULTS`. It is validated at load with `zoneinfo.ZoneInfo`: an unknown name is a `SystemExit`, like the transcription-provider check. The runner's tenant config does not set it, so hosted tenants get the default. zoneinfo resolves in `python:3.12-slim`; checked in the running runner image this session: `2026-09-14 11:15:40+05:00`.
- **Name and caption.** In `Hisab._export_ledger` (`hisab/loop.py:116-127`), `now = datetime.now(ZoneInfo(self.cfg["timezone"]))`, the file is `hisab-{now:%Y-%m-%d-%H%M}.zip`, and the reply is `s("export_ready", lang, when=_when(now))`. `_when` renders `14 Sep 2026, 11:10` from a fixed English month list, so it doesn't depend on locale; the Urdu string supplies its own comma. Two exports in the same minute would reuse a name; that is harmless, because the file is unlinked after each send.
- **Registry.** Add `"export_rejected": Error("chat", None)` to `hisab/errors.py` with `err_export_rejected` in en and ur. Hosted: "WhatsApp wouldn't accept the ledger file, so nothing was sent. The operator has been told." Self-host override: "WhatsApp wouldn't accept the ledger file, so nothing was sent. The reason is in the log." Smoke's registry guards cover the strings automatically.

Invariants kept: six tools (export stays a runner-level command), export contents unchanged (`hisab/archive.py`), 16 MB pre-check unchanged, en/ur strings, failures as codes.

## Success criteria

- [x] `send_document` declares `application/octet-stream` in both the `type` field and the file part, never `application/zip` — `verify: python3 tests/smoke.py`
- [x] An upload refused with `400 / 131053` raises `HisabError("export_rejected")`; the loop replies `err_export_rejected` (no "try again"); a 500 still replies `err_export_failed` — `verify: python3 tests/smoke.py`
- [x] With the clock fixed at `2026-09-14T06:10Z`, the export file is `hisab-2026-09-14-1110.zip` and the caption is `Ledger backup · 14 Sep 2026, 11:10` (en) / `کھاتے کا بیک اپ · 14 Sep 2026، 11:10` (ur) — `verify: python3 tests/smoke.py`
- [x] `timezone` defaults to `Asia/Karachi`, a config can override it, and an unknown zone fails at load — `verify: python3 tests/smoke.py`
- [x] Phone: `export-ledger` delivers a ZIP named `hisab-YYYY-MM-DD-HHMM.zip` in Pakistan time with the short caption, and it unzips to the canonical files — `verify: manual 1. make runner-down && make runner-up (rebuilds the image) 2. send export-ledger to the demo agent 3. expect the document with the caption "Ledger backup · <today>, <local HH:MM>" 4. download, unzip: hisab.md, accounts.md, rules.md, settings.json, the quarter file 5. make runner-logs has no export_failed/export_rejected`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Transport, clock, name, caption, code
**Status:** Done — `send_document` uploads `application/octet-stream` (type field + part), 131053 → `export_rejected`; `timezone` config (default Asia/Karachi, validated); `hisab-YYYY-MM-DD-HHMM.zip` + `Ledger backup · {when}` en/ur; smoke block "export: octet-stream upload…"
- Files: `hisab/wa.py:166-184`; `hisab/config.py:6-19,29-35`; `hisab/loop.py:1-20,116-127`; `hisab/errors.py` (CODES); `hisab/i18n.py` (`export_ready`, new `err_export_rejected[_selfhost]`); `config.example.yaml`; `tests/smoke.py` (export block ~line 193-240)
- Change: as in Approach. `export_ready` becomes en `"Ledger backup · {when}"`, ur `"کھاتے کا بیک اپ · {when}"`. `config.example.yaml` gains `timezone: Asia/Karachi  # IANA name; export file names and captions use it`.
- Test:
  - Monkeypatch `wa_mod.requests.request` to capture the `/media` call from a real `WhatsApp("tok")` → assert `files["file"][2] == "application/octet-stream"` and `data["type"] == "application/octet-stream"`.
  - A fake `/media` answer of `400 {"error":{"code":131053}}` → `HisabError` code `export_rejected`; `500` → `RuntimeError`.
  - Loop level with `ExportFakeWA.send_document` raising each → the reply text for each code.
  - `loop_mod.datetime` patched to a fixed `2026-09-14T06:10Z`, en and ur ledgers → assert the filename and caption exactly.
  - `cfgmod.load` on a yaml with `timezone: Mars/Olympus` → `SystemExit`; default → `"Asia/Karachi"`.
  - Loosen the existing `filename.startswith("hisab-export-")` assertion (`tests/smoke.py:221`) to the new pattern.

### Phase 2 — Docs and the phone
**Status:** Done — README export line, ARCHITECTURE failure row; owner's phone run: `hisab-2026-09-14-1119.zip`, caption `Ledger backup · 14 Sep 2026, 11:19`, unzipped to all five canonical files
- Files: `README.md:49` (the ZIP is named by local date and time), `ARCHITECTURE.md` failure table (export row: `export_rejected` vs `export_failed`), `runner/README.md:35` untouched unless wording changes
- Change: the doc lines above; then the manual criterion on the `make up` stack with the demo agent.
- Test: the manual criterion.

## Risks

- The manual doesn't say explicitly that a generic binary may be sent as a `document`; the live probe proved it on 2026-09-14. If the platform tightens this, the refusal now surfaces as `export_rejected` with the detail in the log instead of silently retrying.
- A self-hoster outside Pakistan sees Pakistan time until they set `timezone`, which `config.example.yaml` documents.

## Out of scope

- Entry dates: the agent's "Today is" (`hisab/agent.py:51`, `date.today()`) is also UTC in the container, so entries sent 00:00–05:00 PKT get yesterday's date. That's a separate issue, and it can reuse the `timezone` key this adds.
- Delivery by download link (#33) and any change to what the ZIP contains.
