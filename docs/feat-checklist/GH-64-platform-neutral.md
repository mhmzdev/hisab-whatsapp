---
type: Checklist
title: GH-64-platform-neutral — acceptance checklist
description: Review of dropping the Android-only wording from the README, ARCHITECTURE, the landing page and the hosted-portal brainstorm and spec, against issue #64.
tags: [checklist, landing, docs]
timestamp: 2026-09-20T00:00:00Z
---

# GH-64-platform-neutral — acceptance checklist   (7 proven · 2 manual · 0 failing)

Scope: 6 files on `GH-64-platform-neutral`: `README.md`, `ARCHITECTURE.md`, `docs/brainstorm/hosted-portal.md`, `docs/specs/001-hosted-portal.md`, `landing/app/page.jsx`, `landing/content/strings.json`. Intent: [#64](https://github.com/mhmzdev/hisab-whatsapp/issues/64) "What to change" and "Done when", plus the lead's ruling that the two lines the sweep found (README intro blurb, brainstorm "Problem") are in scope. No exec plan: a wording change, `/create-plan` skipped.

- [x] Nothing says Hisab or WhatsApp agents are limited to one platform — `grep -rniI -e android -e iphone -e "\bios\b"` (excluding `node_modules`, `.next`, `out`, `.git`) finds only `landing/app/layout.jsx:27`, the 180 px iOS home-screen icon size, left alone by decision
- [x] `README.md:99` and the intro blurb (`README.md:16`) are platform-neutral — same grep
- [x] `ARCHITECTURE.md:56` reads "without a WhatsApp agent" — same grep
- [x] Brainstorm `:16`, `:20` drop "Android"; brainstorm `:116` and spec `:110` drop the iOS out-of-scope entries; nothing else in either doc changed — `git diff main...HEAD -- docs/` shows only those four lines
- [x] `hero_platforms` is `WhatsApp · English · اردو` / `WhatsApp · انگلش · اردو`, and `footer_note` is gone from `strings.json` and `page.jsx` — `python3 tests/check_landing.py` passes (en and ur complete); `grep -rn footer_note` finds nothing
- [x] The landing page builds and the footer has no empty element — `npm run build` with `NEXT_PUBLIC_USE_EMULATORS=1 NEXT_PUBLIC_HOSTED=0` exported `/` and `/portal`; `out/index.html` footer row is logo · Hisab · tagline · GitHub · "Built in Islamabad", zero empty spans, zero "android". The footer row is a wrapping flex row with a gap, so one item fewer needs no CSS change
- [x] Repo check passes — `python3 tests/smoke.py` prints ALL OK
- [?] The footer reads right to the eye — `make landing && make landing-serve`, open the page, look at the footer at desktop and phone width in English and in اردو
- [?] Post-merge, owner: deploy the landing page — `make landing-pages-deploy`

## Conventions

Surface, writes, transport and the dashboard conventions are untouched: no Python under `hisab/` changed. Language: no new user-facing string; `i18n.py` had no platform wording. Privacy: the diff carries no personal detail. Docs: the README stays true.

## Findings

None.
