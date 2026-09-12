---
type: Index
title: exec-plans
description: Implementation plans and where each one is in its life. A plan is a contract — no open questions — and moves between the four directories as work progresses.
tags: [index, plans]
timestamp: 2026-09-12T00:00:00Z
---

# exec-plans

Up: [docs/INDEX.md](../INDEX.md). Written by `/create-plan` into `backlog/`; `/implement` moves a plan to `active/` on start and `completed/` on finish; a plan overtaken by events goes to `superseded/` with a line saying by what.

## Backlog
| Plan | Problem it solves | Depends on |
|---|---|---|

## Active
| Plan | Started | Issue |
|---|---|---|

## Completed
| Plan | Shipped | Summary |
|---|---|---|
| [GH-3-hosted-landing-portal-shell](completed/GH-3-hosted-landing-portal-shell.md) | 2026-09-12 | Static Next.js landing page + four-state portal shell (mocks only); `tests/check_landing.py` wired into smoke |

## Superseded
| Plan | Superseded by |
|---|---|
