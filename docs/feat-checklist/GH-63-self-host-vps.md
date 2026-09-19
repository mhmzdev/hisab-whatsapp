---
type: Checklist
title: GH-63-self-host-vps — acceptance checklist
description: Review of the self-host VPS guide (one ask/do prompt for a coding agent), its README link and INDEX row, and the down -v wording fixed in AGENTS.md and the Makefile, against issue #63.
tags: [checklist, self-host, docs]
timestamp: 2026-09-20T00:00:00Z
---

# GH-63-self-host-vps — acceptance checklist   (7 proven · 1 manual · 0 failing)

Scope: 5 files on `GH-63-self-host-vps`: `docs/self-host-vps.md` (new), `README.md`, `docs/INDEX.md`, `AGENTS.md`, `Makefile`. Intent: [#63](https://github.com/mhmzdev/hisab-whatsapp/issues/63) "Done when", plus the lead's rulings: the step 7 log line, and correcting the `down -v` wording in AGENTS.md and the Makefile. Docs work, so `/create-plan` was skipped (AGENTS.md: small, low-risk work may skip stages). No live run: no VPS, no SSH, no `docker compose up` against an agent.

- [x] `docs/self-host-vps.md` exists: a short intro and one fenced `text` prompt with the 11 ask/do steps of #63 in order. Provider names were grepped for (`hetzner|digitalocean|linode|vultr|aws|contabo|oracle cloud|android`): none found. Step 1 says "Do not recommend a provider".
- [x] The env names match `.env.example`. `grep '^WHATSAPP_TOKEN=' / '^OPENROUTER_API_KEY=' / '^GEMINI_API_KEY='` all hit.
- [x] The config keys match `config.example.yaml`. `timezone:` is on line 8, `ledger: currency:` on line 6. Step 5 sets both, because the setup answer is not read back after a restart (tracked separately).
- [x] The compose facts match `docker-compose.yml`: `restart: unless-stopped`, the `hisab-data` volume, and no `ports:` (0 hits). So the no-inbound-port claim holds. Plain `docker compose up -d --build` is used, and `make selfhost` is ruled out because it depends on `landing landing-up` (`Makefile:13`).
- [x] The log strings the prompt waits on exist in the code: `"Polling WhatsApp."` (`hisab/loop.py:173`, with the path deliberately not quoted, since `hisab/config.py:56` makes it absolute), `WHATSAPP_TOKEN is empty` (`hisab/loop.py:168`), `; exiting` (`hisab/loop.py:181`), `another poller is using this agent` (`hisab/wa.py:108-109`), and `export-ledger` (`hisab/loop.py:55`).
- [x] The README's "Run it for real" links to the guide after step 5 (`README.md:107`), and README line 99 is untouched. `docs/INDEX.md` lists the guide under a new "Guides" section. The guide's anchors `#run-it-for-real`, `#what-you-can-send` and `#viewing` resolve to README headings.
- [x] The `down -v` wording now agrees in three places: the guide's rules, the AGENTS.md Docker table row, and the `make help` text for `selfhost-down-v`, checked with `make help | grep selfhost-down-v`. The repo check passes: `python3 tests/smoke.py` → `ALL OK`.
- [?] Post-merge, owner + lead: a coding agent runs the prompt against a fresh VPS until WhatsApp replies. Paste the fenced prompt into a coding agent, answer its questions, fill `.env` on the server by hand, send the agent "hi", and expect an `in` line and an `out` line in `docker compose logs` and a setup question on the phone.

## Findings

None against AGENTS.md. Privacy: `grep '/Users/|hamza|+92'` on the guide finds nothing. `.env`, `config.yaml` and `vault/` do not exist in the worktree and were not touched.
