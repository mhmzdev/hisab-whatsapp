---
name: open-pr
description: Open or update the PR for the current branch against main with the fixed body shape (Why in plain English, Change Summary, Major Impact, Linked Issue, Test Plan seeded from the feat-checklist). Rescues work stranded on main onto a branch. Confirms before any push; never force-pushes; never pushes to main. Use when the user says "open a PR", "ship this", "put this up for review".
argument-hint: "[title hint | issue number] [--base <branch>]"
---

# Open PR

Honour `.agents/skills/README.md`. Last step: `… → /review → **/open-pr**`. Only on request; it is outward-facing. **Never push, commit or `gh pr create` without the user's confirmation (Phase 5).**

Facts from `AGENTS.md`: `trunk` = `main`, `issues_repo` = `mhmzdev/hisab-whatsapp`, labels = only what `gh label list` returns (none is fine), attribution = **keep** (the repo's commits carry the Claude trailer; the PR body ends with the standard line and the session link — copy the form from `git log -3`).

## Phase 1 — State
In parallel: `git status --short`, `git branch --show-current`, `git fetch origin --quiet`, `git log --oneline origin/main..HEAD`, `gh pr view <branch> --json number,state,url` (existing PR?), `gh auth status`.
- Feature branch, commits ahead, clean → **Flow A**.
- Feature branch, dirty → ask: include these files or not? Stage only named files.
- On `main` with commits ahead or a dirty tree → **Flow B** (rescue): branch off HEAD first (`git checkout -b GH-<N>-<topic>` or `<topic>`), then `git branch -f main origin/main`. Dirty tree: `git stash push -u`, checkout main, `pull --ff-only`, branch, `stash pop`. Never `reset --hard`; stop on conflict.
- Existing open PR → **update** it (`gh pr edit`), never a duplicate.

## Phase 2 — Linked issue
First match wins, never invented: numeric argument → the plan's frontmatter `issue:` for this branch → `GH-<N>` in the branch name → `Closes #N` in commit messages → `gh issue list --search` only if unambiguous (confirm). Verify with `gh issue view N`. Found → `Closes #N`; not found → `_None._`.

## Phase 3 — Title and body
**Title**: conventional-commit shape, imperative, under ~70 chars, matching `git log` on `main`.

**Body**, headings verbatim, in this order; `_None._` where honestly nothing, except Why, which is never empty:

```markdown
## Why
<2–4 plain-English sentences for someone who has not seen the diff: what was wrong or missing, who it affected, what is true once this merges. Link the issue inline. No paths, no symbols.>

## Change Summary
<2–4 factual sentences for the reader who will open the diff: approach, files, what was chosen over the obvious alternative. Reference the plan path.>

## Major Impact
<One bullet per concrete breakage risk: a tool schema change, a store record shape, a ledger convention, a config key, a language string. Else _None._>

## Linked Issue
<Closes #N, or _None._>

## Test Plan
<Unchecked boxes seeded from docs/feat-checklist/<slug>.md: each [?] becomes a manual step verbatim; each [x] with a named test becomes "`<test>` passes"; a [!] means stop and say so. No checklist → one box per substantive change. Always end with: `- [ ] python3 tests/smoke.py — clean` (no CI runs it yet).>

## Deploy prerequisites
<Only when needed: a new config key (config.example.yaml), a new env var (.env.example), a Docker change that needs a rebuild. Omit otherwise.>
```

Write the body to a tempfile. End it with the attribution line and session link the repo's commits use.

## Phase 4 — Labels
Only labels that exist and fit; none is the normal case.

## Phase 5 — Confirm and wait
```
Branch: <branch> → main    (new PR | updating #N)
Title:  <title>      Labels: <list|none>
Commits: <n> — one line each
Flow B plan, if any
<rendered body>
Push and open/update the PR?
```
Any redirect → apply and re-present. Never proceed on silence.

## Phase 6 — Execute and verify
`git push -u origin <branch>`; `gh pr create --repo mhmzdev/hisab-whatsapp --base main --head <branch> --title … --body-file …` (or `gh pr edit`). Then `gh pr view --json number,title,url,baseRefName,body`: every required heading present, else fix. `gh issue develop <N>` to link. Report: URL, title, base, created vs updated, every Deploy prerequisite bullet verbatim, the unchecked Test Plan items.

## What NOT to do
- Force push, push to `main`, `reset --hard`, stash without `-u`, auto-resolve a conflict, `git add -A` unasked. Open without confirmation. Duplicate a PR. Fabricate or omit `Closes #N`. Write the Why in code or as a restatement of the summary. Tick a Test Plan box. Move the board card.
