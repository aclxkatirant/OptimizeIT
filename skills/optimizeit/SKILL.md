---
name: optimizeit
description: Use when an existing application is slow, heavy, resource-hungry or does not scale - slow startup, high CPU or memory, memory leaks, slow API responses, slow or N+1 database queries, large JavaScript bundles, unnecessary re-renders, event loop blocking, redundant network requests, bloated dependencies, slow builds - or when the user asks to optimize, speed up, profile, benchmark or find bottlenecks, in any language, or invokes "OptimizeIT".
---

# OptimizeIT

## Overview

OptimizeIT works like a senior software performance engineer: it makes an existing application faster, lighter and more stable **without breaking its functionality**.

**Core principle:** Do not optimize what you have not measured, and do not call done what you have not verified. Every change rests on a finding, every finding on evidence, every claimed improvement on a measurement.

OptimizeIT is not a best-practices checklist reader. **It analyzes, optimizes, tests, measures and reports.**

**Language:** Write findings and the final report in the user's language.

## When to Use

- The user wants a project (or a module, endpoint, page, query) to be faster or more efficient.
- There is a symptom: slowness, high CPU, growing memory, timeouts, leaks, large bundles, slow builds.
- A code review surfaced a performance-risky pattern (query inside a loop, synchronous I/O on a hot path, unbounded cache).

**Do not use for:** writing new features from scratch, pure style/format cleanups, security-only audits with no performance angle.

**Scope:** If the user names a target ("`/api/orders` is slow"), analyze that path end to end. If not, scan the whole project but limit changes to the highest-value findings.

## Non-Negotiable Rules

1. Never modify code whose purpose you do not understand.
2. Never optimize blindly: every change needs a technical justification and evidence.
3. Never remove functionality, change behavior, or skip validation/security checks to get better numbers.
4. Never add unnecessary dependencies; never duplicate existing functionality.
5. Never rewrite a module when a targeted change is sufficient.
6. Never assume a framework or runtime version; read it from manifests and lockfiles.
7. **Never invent benchmark results.** If it was not measured, write "not measured".
8. Never claim tests passed if they were not executed.
9. Never introduce a security vulnerability for performance (e.g. replacing parameterized queries with string concatenation, caching authorization decisions across users).
10. Never touch unrelated files. Do not open secrets (`.env`, keys, credentials) unless required; never put them in the report.
11. **Never** apply destructive database migrations automatically (DROP, column removal/alteration, data rewrites). Explain schema changes and ask for approval.
12. Never change public APIs, configuration behavior or the UI without explicit authorization.
13. Never ignore existing bugs in code you modify: report them (as a separate finding if needed).
14. Follow the project's existing coding conventions.

## Workflow (8 Phases)

Run the phases in order. If a phase is skipped, **write the reason into the report** (e.g. "no test infrastructure", "application cannot run in this environment").

```
1 DISCOVERY → 2 ANALYSIS → 3 PRIORITIZATION → 4 BASELINE → 5 OPTIMIZATION → 6 VALIDATION → 7 BENCHMARK → 8 REPORT
                                                    ↑                                    │
                                                    └──────── on regression, go back ────┘
```

### Phase 1 — Discovery

Goal: understand the application before changing it.

1. Run the discovery script (requires Python 3.8+; if unavailable, collect the same facts manually):
   ```
   python <skill-dir>/scripts/discover.py <project-dir>
   ```
   It reports languages, frameworks/libraries, package managers, build systems, entry points, database technologies, external services, test/lint/typecheck/build commands and the largest source files.
2. **Verify** the output: actually read the manifests (`package.json`, `pyproject.toml`, `composer.json`, `pom.xml`, `*.csproj`, `go.mod`, `Cargo.toml`, ...) and the entry points.
3. Map the architecture: layers, internal module dependencies, request lifecycle, data flow, background jobs, external integrations.
4. Trace the target bottleneck path (the flow the user complains about) end to end.
5. Check `git status`. If the user has uncommitted changes, do not overwrite them; report the state.

**Gate:** Do not enter Phase 2 until the stack and the relevant entry points are identified.

### Phase 2 — Analysis

Goal: find real bottlenecks, not merely suspicious patterns.

1. Walk the categories in `references/analysis-checklist.md`.
2. Load the references that match the detected stack:
   - Database present → `references/database.md`
   - Frontend present → `references/frontend.md`
   - Backend/service present → `references/backend.md`
   - Language/framework-specific patterns and profilers → `references/languages-and-frameworks.md`
3. **Profile** when possible (CPU profile, heap snapshot, query log, `EXPLAIN`, bundle analysis). A profile beats a guess.
4. Judge every suspicious pattern **in context**:
   - Is it on a hot path (called often, per request, inside a loop)?
   - How large is the data really? (O(n²) on a 10-item list is not a problem.)
   - Is the impact measurable or only theoretical?
5. Record each finding in the **Finding Format** below.

**Gate:** A finding whose real impact has not been assessed is labeled "unverified suspicion" and cannot be rated CRITICAL or HIGH.

### Phase 3 — Prioritization

| Priority | Meaning |
|---|---|
| **CRITICAL** | Severe issue affecting stability or usability (leak → crash, timeouts, event loop lockup, N+1 that makes a page unusable in production). |
| **HIGH** | Significant degradation (avoidable O(n²) on a hot path, unindexed scan of a large table, expensive per-request recomputation). |
| **MEDIUM** | Noticeable inefficiency with measurable improvement potential. |
| **LOW** | Minor optimization opportunity. |
| **INFORMATIONAL** | Architectural observation or future improvement. |

Order implementation by **value / risk**. Category order: critical bottlenecks → CPU → memory → database → network → algorithms → overhead → maintainability.

Select the findings to implement. Anything requiring a schema change, public API change, new dependency or behavior change: **ask the user before implementing**; without approval, list it as a recommendation.

### Phase 4 — Baseline

Goal: pin down the "before" value with evidence.

1. For each selected finding, pick the relevant metric (execution time, CPU, memory, startup, query duration, API latency, throughput, request count, bundle size, build duration).
2. Build a repeatable measurement command (benchmark script, test, HTTP load tool, build command). Details: `references/measurement-and-benchmarking.md`.
3. Run it through the measurement script:
   ```
   python <skill-dir>/scripts/measure.py run --name before --runs 10 --warmup 2 --output .optimizeit/before.json -- <command>
   ```
4. If measurement is impossible (no data, no service, no environment), record that and why. The improvement is then reported as **"not measured"**.

Keep measurement files in the target project under `.optimizeit/`; ask the user whether that folder should be committed.

### Phase 5 — Optimization

1. Implement **one finding at a time**; keep changes small and reviewable.
2. Before changing code, find affected modules, callers and tests (search for every usage).
3. Preserve behavior: same inputs → same outputs, same error cases, same side effects, same ordering (when ordering is part of the contract).
4. When adding a cache: define invalidation, size bound, TTL, concurrency behavior, and the risk of leaking per-user data.
5. When adding concurrency: check shared state, races, ordering guarantees, error propagation and resource limits (connection pools, rate limits).
6. Record the justification of each change in its finding.

### Phase 6 — Validation

After each change (or coherent group of changes), run whatever the project **actually has**:

- tests
- linting
- type checking
- build
- targeted validation of the modified component (e.g. a comparison showing old and new implementations return identical results for identical inputs)

Rules:
- If a test fails, first check **whether it failed before the optimization** (stash the change or compare with earlier results). If it was already failing, report it as a pre-existing bug.
- **Do not declare the task complete while a regression you introduced remains.** If it cannot be fixed, revert the change and report it.
- With no test infrastructure, write a temporary behavior-comparison script for the modified function (in a scratch location; do not add permanent files to the project without permission).
- Keep the real output of every command; you may only say "passed" after seeing it.

### Phase 7 — Benchmark

1. Rerun the **same command with the same data in the same environment** as Phase 4:
   ```
   python <skill-dir>/scripts/measure.py run --name after --runs 10 --warmup 2 --output .optimizeit/after.json -- <command>
   python <skill-dir>/scripts/measure.py compare .optimizeit/before.json .optimizeit/after.json
   ```
2. If the difference is within measurement noise, say "no significant improvement"; do not claim one.
3. If something got worse, reassess the change and revert if needed.

### Phase 8 — Report

Produce the report from `references/report-template.md`. Ten required sections:

1. Project Overview
2. Technologies Detected
3. Initial Performance Findings
4. Identified Bottlenecks
5. Implemented Optimizations
6. Modified Files
7. Performance Comparison
8. Tests and Validation
9. Remaining Issues
10. Final Assessment

The report **clearly separates** four states: *discovered* / *implemented* / *validated* / *recommended (not implemented)*.

Show the report to the user and save it in the target project as `.optimizeit/REPORT.md`.

## Finding Format

Every finding contains **all** of these fields:

```markdown
### [PRIORITY] OPT-<n>: <Title>
- **Location:** `path/file.ext:line` (function/component)
- **Technical explanation:** What happens?
- **Root cause:** Why does it happen?
- **Performance impact:** Measured or reasoned estimate (state which).
- **Recommended solution:** What should be done?
- **Implementation risk:** Low / Medium / High + why
- **Implemented:** Yes / No (why) / Awaiting approval
- **Validation result:** Commands run and their results / "not validated"
```

## Red Flags — STOP

If one of these thoughts appears, stop and return to the relevant phase:

| Thought | Reality |
|---|---|
| "This pattern is obviously slow, no need to measure." | Impact is unknown without context. Hot path? Data size? Measure, or write "not measured". |
| "It is probably about 40% faster." | Invented number. No measurement, no percentage. |
| "The tests will probably pass." | If you did not run them, write "not run". |
| "Rewriting this module would be cleaner." | Rewrites are forbidden when a targeted change suffices. |
| "Adding this library makes it easy." | New dependencies need approval; solve with existing tools first. |
| "I'll just apply this index migration too." | Schema changes are explained and approved. Destructive migrations are never automatic. |
| "This validation step is slow, I'll remove it." | Removing functionality or security is not optimization. |
| "The test broke, but it was unrelated anyway." | Check the pre-change state first. No evidence, no "unrelated". |
| "The difference is small, but I'll call it an improvement." | A difference inside the noise is not an improvement. |
| "One more micro-optimization can't hurt." | No change that hurts readability without a measurable gain. |

## Reference Files

| File | Load when |
|---|---|
| `references/analysis-checklist.md` | Always, in Phase 2 |
| `references/database.md` | An ORM, SQL or NoSQL store is detected |
| `references/frontend.md` | Browser code or a UI framework is detected |
| `references/backend.md` | A server, API, worker or service is detected |
| `references/languages-and-frameworks.md` | Choosing language/framework-specific patterns and profilers |
| `references/measurement-and-benchmarking.md` | Phases 4 and 7 |
| `references/report-template.md` | Phase 8 |

## Scripts

| Command | Purpose |
|---|---|
| `python scripts/discover.py <dir> [--json]` | Project discovery: languages, frameworks, package managers, entry points, databases, commands |
| `python scripts/measure.py run ...` | Runs a command N times and records wall-time and peak-memory statistics (JSON) |
| `python scripts/measure.py compare before.json after.json` | Compares two measurements; prints a Markdown table with a noise warning |

Scripts use only the Python standard library. Always invoke them through the interpreter (`python ...`; use `python3` where `python` is not available).

## Quick Reference

- **Understand → measure → change → validate → measure again.**
- One finding at a time. Test after every change.
- No measurement → no number. Tests not run → no "passed".
- Schema / public API / dependency / behavior change → approval first.
- Report: discovered ≠ implemented ≠ validated ≠ recommended.
