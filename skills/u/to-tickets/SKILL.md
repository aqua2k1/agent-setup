---
name: to-tickets
description: >
  Break a spec into tracer-bullet tickets with blocking edges,
  written as individual files under .scratch/<slug>/issues/.
disable-model-invocation: true
---

Break a spec or plan into a set of **tracer-bullet tickets** — vertical slices
that each cut a narrow but complete path through every layer. Each ticket
declares its **blocking edges** (the tickets that must complete before it can
start) and lives as an independent file under `.scratch/<slug>/issues/`.

## Process

### 1. Gather context

Work from the spec in the conversation. If the user passes a path to a spec
file, read it. Also read `CONTEXT.md` for domain vocabulary.

### 2. Explore the codebase (if needed)

Understand the current state to inform the breakdown.

### 3. Draft vertical slices

Break the work into tickets. Rules:

- Each slice cuts a narrow but COMPLETE path through every layer
- A completed slice is demoable on its own
- Each slice fits in a single fresh context window
- Prefactoring (make the change easy first) goes first

**Wide refactors are the exception**: one mechanical change whose blast radius
fans across the codebase. Don't force it into a tracer bullet. Sequence as
expand–contract: add new form → migrate callers in batches → remove old form.
Each batch is its own ticket, blocked by the expand ticket.

### 4. Quiz the user

Present the breakdown as a numbered list. For each ticket show:

- **Title**
- **Blocked by** — which tickets must complete first
- **What it delivers** — end-to-end behaviour

Ask: granularity right? blocking edges correct? merge or split anything?
Iterate until approved.

### 5. Write the ticket files

Ask the user for the feature slug (or reuse from /to-spec).

Write one file per ticket under `.scratch/<slug>/issues/`, numbered `01`
upwards in dependency order (blockers first). Use this template:

```markdown
# NN — Ticket Title

**What to build:** the end-to-end behaviour this ticket makes work,
from the user's perspective — not a layer-by-layer implementation list.

**Blocked by:** the ticket numbers/titles that gate this one,
or "None — can start immediately".

**Status:** ready

- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2
```

A ticket with no blockers is **ready**. A ticket whose blockers are all
**done** is **ready**. Work the frontier: any ready ticket can be picked up
by `/implement` in a fresh session.
