---
name: codebase-design
description: >
  Shared vocabulary for designing deep modules — small interfaces, deep
  implementations, clean seams. Use when designing or improving a module's
  interface, deciding where a seam goes, making code more testable or
  AI-navigable, or when another skill needs the deep-module vocabulary.
---

Design **deep modules**: a lot of behaviour behind a small interface, placed
at a clean seam, testable through that interface. Use this language and these
principles wherever code is being designed or restructured. The aim is
leverage for callers, locality for maintainers, and testability for everyone.

## Glossary

Use these terms exactly — don't substitute "component," "service," "API," or
"boundary." Consistent language is the whole point.

**Module** — anything with an interface and an implementation. Deliberately
scale-agnostic: a function, class, package, or tier-spanning slice.
_Avoid_: unit, component, service.

**Interface** — everything a caller must know to use the module correctly: the
type signature, but also invariants, ordering constraints, error modes,
required configuration, and performance characteristics.
_Avoid_: API, signature (too narrow — they refer only to the type-level surface).

**Implementation** — what's inside a module, its body of code. Distinct from
**Adapter**: a thing can be a small adapter with a large implementation (a
Postgres repo) or a large adapter with a small implementation (an in-memory
fake).

**Depth** — leverage at the interface: the amount of behaviour a caller (or
test) can exercise per unit of interface they have to learn. A module is
**deep** when a large amount of behaviour sits behind a small interface,
**shallow** when the interface is nearly as complex as the implementation.

**Seam** — a place where you can alter behaviour without editing in that
place; the *location* at which a module's interface lives. Where to put the
seam is its own design decision, distinct from what goes behind it.
_Avoid_: boundary.

**Adapter** — a concrete thing that satisfies an interface at a seam.
Describes *role* (what slot it fills), not substance (what's inside).

**Leverage** — what callers get from depth: more capability per unit of
interface they learn. One implementation pays back across N call sites and M
tests.

**Locality** — what maintainers get from depth: change, bugs, knowledge, and
verification concentrate in one place rather than spreading across callers.

## Deep vs shallow

See [deep-modules.md](deep-modules.md) for diagrams.

When designing an interface, ask:

- Can I reduce the number of methods?
- Can I simplify the parameters?
- Can I hide more complexity inside?

## Principles

- **Depth is a property of the interface, not the implementation.** A deep
  module can be internally composed of small, mockable, swappable parts — they
  just aren't part of the interface.
- **The deletion test.** Imagine deleting the module. If complexity vanishes,
  it was a pass-through. If complexity reappears across N callers, it was
  earning its keep.
- **The interface is the test surface.** Callers and tests cross the same seam.
  If you want to test *past* the interface, the module is probably the wrong
  shape.
- **One adapter means a hypothetical seam. Two adapters means a real one.**
  Don't introduce a seam unless something actually varies across it.

## Designing for testability

See [interface-design.md](interface-design.md) for patterns.
