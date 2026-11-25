# Report Template (Phase 8)

Save the report to `.optimizeit/REPORT.md` in the target project and show it to the user. Write it in the user's language. Every section is required; if a section has no content, say so explicitly ("No files were modified.").

Status vocabulary (use exactly these labels):
- **Discovered** — identified, not changed
- **Implemented** — code changed
- **Validated** — implemented and checked by tests/builds/measurements that were actually run
- **Recommended** — not implemented (with the reason: needs approval, too risky, out of scope)

---

```markdown
# OptimizeIT Optimization Report

**Project:** <name>
**Date:** <YYYY-MM-DD>
**Scope:** <whole project | specific module/endpoint/page>
**Git state:** <branch, base commit, whether the working tree was clean>

## 1. Project Overview

<What the application does, its architecture (layers, modules, request/data flow), entry points, and the reported or suspected performance problem.>

## 2. Technologies Detected

| Area | Technology | Version (source) |
|---|---|---|
| Language | <e.g. TypeScript> | <5.4.5 (package-lock.json)> |
| Runtime | | |
| Framework | | |
| Database | | |
| Build / package manager | | |
| Test / lint / type check | | |
| External services | | |

## 3. Initial Performance Findings

<How the analysis was done: profiles taken, logs examined, tools used. Summary of what was found, including suspicions that were investigated and ruled out.>

| ID | Priority | Title | Location | Status |
|---|---|---|---|---|
| OPT-1 | HIGH | | `path:line` | Validated |
| OPT-2 | MEDIUM | | | Recommended |

## 4. Identified Bottlenecks

<One block per finding, in priority order, using the finding format:>

### [HIGH] OPT-1: <Title>
- **Location:** `path/file.ext:line` (function/component)
- **Technical explanation:**
- **Root cause:**
- **Performance impact:** <measured: … | estimated (not measured): …>
- **Recommended solution:**
- **Implementation risk:** <Low/Medium/High> — <why>
- **Implemented:** <Yes | No (reason) | Awaiting approval>
- **Validation result:** <commands and results | not validated>

## 5. Implemented Optimizations

<For each implemented finding: what changed, why it is behavior-preserving, any trade-offs (memory for speed, added complexity).>

## 6. Modified Files

| File | Change | Finding |
|---|---|---|
| `src/...` | <short description> | OPT-1 |

## 7. Performance Comparison

**Environment:** <OS, CPU, runtime version, build mode>
**Method:** <exact commands, runs, warm-ups>

| Metric | Before | After | Change | Significant? |
|---|---:|---:|---:|---|
| | | | | |

<Metrics that could not be measured are listed as "not measured" with the reason. Never invent values.>

## 8. Tests and Validation

| Check | Command | Before change | After change |
|---|---|---|---|
| Tests | `<cmd>` | <e.g. 142 passed, 1 failed (pre-existing)> | <…> |
| Lint | | | |
| Type check | | | |
| Build | | | |
| Behavior equivalence | | — | |

<Use these labels for checks that did not run normally: "not available" (the project has no such check), "not run (tool not installed)", "manual invocation" (test functions called directly, not through the runner). Never write "passed" for a check that was not run through its runner. Explain any failure and whether it pre-existed.>

## 9. Remaining Issues

- Recommendations not implemented (with reason and what approval would unlock)
- Proposed schema changes (with SQL, rollback, lock behavior)
- Pre-existing bugs noticed
- Areas not analyzed and why

## 10. Final Assessment

<Short, honest summary: what measurably improved, what was validated, the remaining risks, and the recommended next steps in priority order.>
```
