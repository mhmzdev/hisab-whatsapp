---
type: Index
title: docs — the progressive-disclosure root
description: Start here for anything that is not code. Each directory below has its own INDEX.md; each artifact links to the ones before and after it in the lifecycle.
tags: [index, lifecycle]
timestamp: 2026-09-12T00:00:00Z
---

# docs

Reading order for the whole repo: [`AGENTS.md`](../AGENTS.md) → [`ARCHITECTURE.md`](../ARCHITECTURE.md) → this index → the artifact you need → the code. Product pitch and run instructions: [`README.md`](../README.md).

Format: every document here is markdown with a small YAML frontmatter (`type` required; `title`, `description`, `tags`, `timestamp` when useful), following the [Open Knowledge Format](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing). Plain links between files are the graph. One slug travels every stage: `GH-<N>-<topic>` once an issue exists.

| Directory | Holds | Written by | Read by |
|---|---|---|---|
| [`brainstorm/`](brainstorm/INDEX.md) | WHAT and WHY, before any plan — approaches considered, the one leaned toward, open questions | `/brainstorm` | `/grill-me`, `/to-spec` |
| [`specs/`](specs/INDEX.md) | Numbered WHAT/WHY contracts: problem, solution, user stories, decisions, testing seam. Temporary — once ticketed, the GitHub issue is the truth | `/to-spec` | `/file-an-issue`, `/create-plan` |
| [`exec-plans/`](exec-plans/INDEX.md) | HOW: phased, `file:line`-grounded plans with provable criteria, moving `backlog → active → completed` (or `superseded`) | `/create-plan`, moved by `/implement` | `/implement`, `/review`, `/open-pr` |
| [`feat-checklist/`](feat-checklist/INDEX.md) | Acceptance checklists per slug: what was proven, what needs a human, what failed | `/review` | `/open-pr` (seeds the Test Plan) |

Tickets are **GitHub issues** on [mhmzdev/hisab-whatsapp](https://github.com/mhmzdev/hisab-whatsapp/issues), tracked on the [Hisab Engineering board](https://github.com/users/mhmzdev/projects/1). There is no local ticket file, by design.

Process rules and who owns each board transition: [`.agents/skills/README.md`](../.agents/skills/README.md).
