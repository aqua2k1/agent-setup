---
name: to-spec
description: >
  Turn the current conversation into a spec and write it to
  .scratch/<feature-slug>/spec.md. No interview — just synthesis
  of what you've already discussed.
disable-model-invocation: true
---

Take the current conversation context and produce a spec. Do NOT interview
the user — just synthesize what you already know.

## Process

1. Explore the repo to understand the codebase, if you haven't already.
   Read `CONTEXT.md` for domain vocabulary and respect ADRs in the area.

2. Sketch the seams at which you'll test. Prefer existing seams; propose new
   ones at the highest point possible. Check with the user that these match
   their expectations.

3. Ask the user for a short feature slug (e.g. `user-auth`, `search-v2`).

4. Write the spec to `.scratch/<slug>/spec.md` using the template below.

<spec-template>

# Spec: <title>

## Problem

The problem from the user's perspective.

## Solution

The solution from the user's perspective.

## User Stories

A LONG, numbered list:

1. As a <actor>, I want <feature>, so that <benefit>
2. ...

## Implementation Decisions

- The modules that will be built/modified
- Interfaces that will change
- Architectural decisions
- Schema changes and API contracts

Do NOT include specific file paths or code snippets — they rot fast.
Exception: a prototype-produced snippet that encodes a decision more precisely
than prose can (state machine, schema, type shape). Inline it and note it came
from a prototype.

## Testing Decisions

- Which seams to test at
- What makes a good test here
- Prior art: similar tests in the codebase

## Out of Scope

What's explicitly NOT part of this spec.

</spec-template>
