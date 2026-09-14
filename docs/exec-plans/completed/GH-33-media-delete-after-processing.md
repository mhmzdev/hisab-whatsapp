---
slug: GH-33-media-delete-after-processing
issue: 33
status: completed
open_questions: none
---

# fix: Media is processed then deleted, never stored          ✅ COMPLETED — 2026-09-14

## Problem

[#33](https://github.com/mhmzdev/hisab-whatsapp/issues/33), re-scoped by a grill with the owner on 2026-09-14 (decisions are in the issue comment). Firebase Storage is dropped. Downloaded voice notes and photos land in `data/<uid>/media/` (`hisab/loop.py:38-39`, `:205`, `:214`) and are read exactly once. After that, nothing reads them and nothing prunes them. They grow forever on every install, holding users' voices and receipts with no reader.

## Approach

All of this lives in the shared worker plus one line in the runner. No Firebase, no flag, the same on self-host and hosted.

- **Voice note** (`hisab/loop.py:204-211`): once `transcribe(path, cfg)` returns text, `path.unlink(missing_ok=True)`. On a transcription exception the file stays, same as today.
- **Photo** (`hisab/loop.py:_agent`, the success branch after `self.agent.run(...)` returns): `Path(image).unlink(missing_ok=True)`. On a model exception the file stays. A photo that never reaches the model (quota exceeded, setup active, no ledger) also stays, and the sweep removes it.
- **Sweep.** `MEDIA_TTL = 24 * 3600` and `MEDIA_SWEEP_INTERVAL = 3600` as module constants next to `REMINDER_INTERVAL`. `Hisab._sweep_media(force=False)` deletes regular files directly in `self.media_dir` whose `st_mtime` is older than `MEDIA_TTL`. It runs forced at the end of `__init__` (worker start, and stdin mode too) and from the top of the `run_whatsapp` poll loop, throttled by an in-memory `self._last_media_sweep` timestamp. It only ever touches `media/`. A failure to list or delete is logged to stderr and never raised.
- **Revoke** (`runner/lifecycle.py:35-44`): before moving `data/<uid>`, `shutil.rmtree(Path(runner_cfg["data_root"]) / uid / "media", ignore_errors=True)`.
- **Docs.** The `ARCHITECTURE.md` state-folder row (`:70`) says `media/` is transient: deleted after use, failures swept after 24h. `runner/README.md`'s lifecycle line says revoke deletes media.

Invariants kept: dedup by message id and offset-after-batch are untouched. A crash mid-turn replays and re-downloads by media id. Export never included media. Six tools unchanged.

## Success criteria

- [x] A voice note whose transcription succeeds leaves no file in `media/`, even when the model call then fails; a transcription failure keeps it — `verify: python3 tests/smoke.py`
- [x] A photo whose model call returns leaves no file; a model failure keeps it — `verify: python3 tests/smoke.py`
- [x] At construction and on a due poll-loop sweep, `media/` files older than 24h are removed, while younger files, subfolders and `exports/` stay; a second sweep within the hour doesn't run — `verify: python3 tests/smoke.py`
- [x] Revoke removes `data/<uid>/media/` and still moves the ledger and store to `inactive/` — `verify: python3 tests/smoke.py`
- [x] Phone: after a voice note and a receipt photo post, the tenant's `media/` is empty — `verify: manual 1. make runner-down && make runner-up 2. send a voice note entry and a receipt photo to the demo agent 3. both post 4. docker exec the runner: ls /app/runner-data/data/<uid>/media is empty`
- [x] Repo check passes — `verify: python3 tests/smoke.py`

## Phases

### Phase 1 — Delete after use, sweep, revoke
**Status:** Done — voice unlinked after transcription, photo after `agent.run` returns; `_sweep_media` (24h TTL) at construction + hourly from the poll loop; revoke rmtrees `data/<uid>/media`; smoke "media:" block + revoke assertion; ARCHITECTURE state row, runner README
- Files: `hisab/loop.py:21-23,31-39,84-114,159-172,204-218`; `runner/lifecycle.py:35-44`; `ARCHITECTURE.md:70`; `runner/README.md` (lifecycle line); `tests/smoke.py`
- Change: as in Approach.
- Test (smoke, "media:" block):
  - `VoiceFakeWA` (download returns a real temp file in `media_dir`) with `loop_mod.transcribe` returning text and a `RaisingAgent` → the file is gone; `transcribe` raising → the file exists.
  - An image through a fake agent that returns → the file is gone; a `RaisingAgent` → it exists.
  - Files with `os.utime` at 25h and 1h old, a subfolder, and `exports/x.zip` 25h old → a fresh `Hisab(...)` removes only the 25h media file. `_last_media_sweep` set to now → `_sweep_media()` doesn't run; set to 2h ago → it does.
  - Extend the revoke block: plant `data/<uid>/media/a.ogg` before `poll_revokes` → the moved `inactive/.../data` has no `media/`, and `vault` and the store files are there.

### Phase 2 — Phone
**Status:** Done — owner, hosted `make up` stack: a voice note posted #2 and its `.ogg` was gone; a receipt photo got the model's category question and its `.jpg` was gone; the 06:01Z failed-transcription `.ogg` stayed (under 24h); answering the question ("Lend to a friend") posted #3 without the photo
- The manual criterion, with the owner.

## Risks

- The first start after upgrading deletes existing media older than 24h on every install. That's accepted in the grill and stated in the PR.
- A voice note deleted after transcription can't be re-transcribed if the transcript was wrong; the user resends. Accepted: nothing re-read it before either.

## Out of scope

- Firebase Storage, `storage.rules`, a Storage emulator: dropped by the grill.
- Pruning `exports/`, which already unlinks after each send.
