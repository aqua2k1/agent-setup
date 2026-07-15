---
name: implement
description: >
  Build the work described by a ticket file. Use when the user wants to
  implement a ticket from .scratch/, says "implement this", "build
  ticket-N", or "continue the plan".
disable-model-invocation: true
---

Implement the work described by a ticket file under `.scratch/`.

## Before starting

1. Read `CONTEXT.md` (if it exists) for domain vocabulary.
2. Identify the ticket. In priority order:
   - User passed a path (e.g. `/implement .scratch/search/issues/02-index.md`)
   - User named a ticket number
   - Scan `.scratch/` for the first ticket with **Status: ready**
3. Read the ticket file. Check each blocking ticket: its file should have
   **Status: done**. If any blocker is not done, tell the user and stop.
4. Change the ticket's status to `Status: in-progress`.

## During

1. Read `spec.md` in the same `.scratch/<slug>/` directory for the full spec
   context.
2. Use `/tdd` at the seams agreed in the spec's Testing Decisions section.
3. Run typecheck regularly; full test suite once at the end.
4. Run `/code-review` before committing.

## After

1. Commit.
2. In the ticket file: change `Status: in-progress` to `Status: done` and
   check off all acceptance criteria with `[x]`.
3. Stop. The next ticket starts in a fresh session.
