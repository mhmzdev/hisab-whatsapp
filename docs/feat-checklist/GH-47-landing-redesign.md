---
type: Checklist
title: GH-47-landing-redesign
description: Acceptance checklist for the landing page redesign — GitHub links in a new tab, an icon library instead of emoji, and the HisabPage design with the language and theme controls kept.
tags: [checklist, landing, design]
timestamp: 2026-09-14T00:00:00Z
---

# GH-47-landing-redesign — acceptance checklist   (5 proven · 3 manual · 0 failing)

- [x] Every GitHub link on the landing page opens in a new tab — built `landing/out/index.html` has 3 GitHub links, all `target="_blank" rel="noopener noreferrer"` (one `External` component, `landing/app/page.jsx:15`)
- [x] No emoji or glyph used as an icon in `landing/app/` or `landing/content/mock.js` — a scan for emoji and symbol code points over `landing/app/**/*.js*` and `mock.js` finds none (after the FINDING-01 fix)
- [x] Every new string ships in `en` and `ur` — `python3 tests/check_landing.py` passes
- [x] `npm run build` in `landing/` succeeds — static export of `/` and `/portal`
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`
- [?] Page matches `HisabPage.dc.html` section by section — browser: `make landing && make landing-up`, open http://localhost:3030 at 1280px and 400px, compare each section with the design in light and dark
- [?] Language switcher and theme toggle still work — browser: click اردو, expect the page RTL in Urdu with the phone mock and English shop column still LTR in Inter; click the theme button through System → Light → Dark, expect the icon to change (monitor/sun/moon), the header logo to swap, and the footer logo to stay bright green
- [?] No horizontal scroll at phone width — browser at 400px: `document.documentElement.scrollWidth <= innerWidth` (was 385 ≤ 400 in dark English during implementation; re-check in Urdu)

## Findings
FINDING-01 · Important · fixed (lucide `Check`) · landing/app/portal/page.jsx:273 — the portal's Copy button flips to a `✓` text glyph; issue #47 asks for no glyph icons in `landing/app/`. Swap for lucide `Check`.
FINDING-02 · Important · fixed (English example: “paid Metro 20000”) · landing/content/strings.json:35 — `card_text_body.en` quotes Roman Urdu ("Metro ko 20000 diye"), against the strings contract in landing/README.md:31 ("The page has no Roman Urdu"). The design copy has it; either use an English example or record the exception in the README.
FINDING-03 · Minor · fixed (README “Fonts” section) · landing/README.md:35 — the page now loads Inter, IBM Plex Mono and Noto Nastaliq Urdu through `next/font/google`, which downloads them at build time: `make landing` needs network. The README does not say so.
