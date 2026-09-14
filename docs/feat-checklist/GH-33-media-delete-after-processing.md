---
type: Checklist
title: GH-33-media-delete-after-processing
description: Acceptance checklist for media being processed then deleted — never stored — with a 24h sweep for failed turns and a purge on revoke.
tags: [checklist, media, privacy, runner]
timestamp: 2026-09-14T00:00:00Z
---

# GH-33-media-delete-after-processing — acceptance checklist   (6 proven · 0 manual · 0 failing)

Plan: [GH-33-media-delete-after-processing](../exec-plans/completed/GH-33-media-delete-after-processing.md) · Issue: [#33](https://github.com/mhmzdev/hisab-whatsapp/issues/33) (re-scoped by a grill on 2026-09-14; Firebase Storage dropped)

- [x] A transcribed voice note leaves no file, even when the model call then fails; a failed transcription keeps it — `python3 tests/smoke.py` ("media: …")
- [x] A photo whose model call returns leaves no file; a model failure keeps it — same test
- [x] Media older than 24h is swept at construction and by a due poll-loop sweep; younger files, subfolders and `exports/` stay; the sweep is throttled to once an hour — same test
- [x] Revoke deletes `data/<uid>/media/` while `vault/` and the store still move to `inactive/` — `python3 tests/smoke.py` ("runner: revoke + retention ok")
- [x] Phone (owner, hosted `make up`, rebuilt runner): a voice note posted #2 and its `.ogg` was deleted; a receipt photo got the model's question and its `.jpg` was deleted; the answer "Lend to a friend" posted #3 without the photo; the 06:01Z failed-transcription `.ogg` stays until it is 24h old
- [x] Repo check passes — `python3 tests/smoke.py` → `ALL OK`

## Conventions
- No Firebase in `hisab/`; the only runner change is one `rmtree` in `revoke`. Six tools, dedup and offset unchanged; a crash replays and re-downloads by media id.
- No new strings or config keys.

## Findings
_None in scope._ Follow-up filed from the phone run: #43, transfer receipts don't say whether money went to or from the user (needs a grill).
