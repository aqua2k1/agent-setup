---
name: diagnosing-bugs
description: >
  Diagnosis loop for hard bugs and performance regressions: reproduce →
  minimise → hypothesise → instrument → fix → regression-test. Use when
  user says "diagnose"/"debug this", or reports something broken/throwing/
  failing/slow.
---

# Diagnosing Bugs

A discipline for hard bugs. Skip phases only when explicitly justified.

When exploring the codebase, read `CONTEXT.md` (if it exists) to get a clear
mental model of the relevant modules, and check ADRs in the area you're
touching.

## Phase 1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a **tight**
pass/fail signal for the bug — one that goes red on _this_ bug — you will find
the cause. If you don't have one, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to
give up.**

### Ways to construct one — try them in roughly this order

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e
2. **Curl / HTTP script** against a running dev server
3. **CLI invocation** with a fixture input, diffing stdout against a
   known-good snapshot
4. **Headless browser script** (Playwright / Puppeteer)
5. **Replay a captured trace** — save a real network request / payload / event
   log to disk; replay it through the code path in isolation
6. **Throwaway harness** — spin up a minimal subset of the system with a
   single function call
7. **Property / fuzz loop** — run 1000 random inputs, look for the failure
   mode
8. **Bisection harness** — automate "boot at state X, check, repeat" so you
   can `git bisect run` it
9. **Differential loop** — run the same input through old-version vs
   new-version, diff outputs
10. **HITL bash script** — last resort. If a human must click, drive _them_
    with a structured script so the loop is still structured

Build the right feedback loop, and the bug is 90% fixed.

### Tighten the loop

Once you have _a_ loop, **tighten** it:
- Can I make it faster?
- Can I make the signal sharper?
- Can I make it more deterministic?

A 30-second flaky loop is barely better than no loop; a 2-second deterministic
one is a debugging superpower.

### Non-deterministic bugs

The goal is not a clean repro but a **higher reproduction rate**. Loop the
trigger 100×, parallelise, add stress, narrow timing windows, inject sleeps. A
50%-flake bug is debuggable; 1% is not.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for: (a) access
to the environment that reproduces it, (b) a captured artifact, or (c)
permission to add temporary production instrumentation. Do **not** proceed to
hypothesise without a loop.

### Completion criterion — a tight loop that goes red

Phase 1 is done when the loop is **tight** and **red-capable**: you can name
**one command** you have **already run at least once** that is:
- [ ] **Red-capable** — drives the actual bug code path and asserts the
      **user's exact symptom**
- [ ] **Deterministic** — same verdict every run
- [ ] **Fast** — seconds, not minutes
- [ ] **Agent-runnable** — you can run it unattended

If you catch yourself reading code to build a theory before this command
exists, **stop.** No red-capable command, no Phase 2.

## Phase 2 — Reproduce + minimise

Run the loop. Watch it go red — the bug appears.

Confirm:
- [ ] The loop produces the failure mode the **user** described
- [ ] The failure is reproducible across multiple runs
- [ ] You have captured the exact symptom

### Minimise

Shrink the repro to the **smallest scenario that still goes red**. Cut inputs,
callers, config, data, and steps **one at a time**, re-running the loop after
each cut. Done when **every remaining element is load-bearing**.

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them. Single-
hypothesis generation anchors on the first plausible idea.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If `<X>` is the cause, then `<changing Y>` will make the bug
> disappear / `<changing Z>` will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or
sharpen it.

**Show the ranked list to the user before testing.** Don't block on it —
proceed with your ranking if the user is AFK.

## Phase 4 — Instrument

Each probe must map to a specific prediction from Phase 3. **Change one
variable at a time.**

Tool preference:
1. **Debugger / REPL inspection** — one breakpoint beats ten logs
2. **Targeted logs** at the boundaries that distinguish hypotheses
3. Never "log everything and grep"

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at
the end becomes a single grep.

**Perf branch.** For performance regressions, establish a baseline measurement
first, then bisect.

## Phase 5 — Fix + regression test

Write the regression test **before the fix** — but only if there is a
**correct seam** for it (the test exercises the real bug pattern as it occurs
at the call site). If no correct seam exists, that itself is the finding:
note it and flag for architectural improvement.

If a correct seam exists:
1. Turn the minimised repro into a failing test at that seam
2. Watch it fail
3. Apply the fix
4. Watch it pass
5. Re-run the Phase 1 feedback loop against the original scenario

## Phase 6 — Cleanup + post-mortem

Required before declaring done:
- [ ] Original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed
- [ ] Throwaway prototypes deleted
- [ ] The hypothesis that turned out correct is stated in the commit message

**Then ask: what would have prevented this bug?** If the answer involves
architectural change (no good test seam, tangled callers, hidden coupling),
make the recommendation **after** the fix is in.
