# Measurement and Benchmarking (Phases 4 and 7)

## Principles

1. **Same conditions:** same command, same data, same machine, same build mode, same environment variables, similar background load.
2. **Repeat:** at least 5 runs (10 preferred) after 1–2 warm-up runs. Report the median, not the best run.
3. **Look at variance:** if the difference between before and after is smaller than the run-to-run spread, there is no demonstrated improvement.
4. **Measure the right thing:** the metric must match the finding (a query fix → query time/count, not page render time).
5. **Production-like builds:** release/production mode, never debug/dev mode.
6. **Never invent numbers.** If measurement was impossible, write "not measured" and why.

## Choosing a Metric

| Finding type | Metric | How |
|---|---|---|
| Algorithm / CPU | Execution time, CPU time | Benchmark script or test via `measure.py` |
| Memory | Peak RSS, heap size, growth over time | `measure.py` peak memory, heap snapshots, `tracemalloc` |
| Startup | Time to ready | Command that starts the app and exits when ready (e.g. `node -e "require('./app')"`, `python -c "import app"`) |
| Database | Query duration, query count | Query log, `EXPLAIN ANALYZE`, query-count assertions |
| API | p50/p95/p99 latency, throughput, error rate | Load tool (autocannon, wrk, hey, k6) |
| Network | Request count, transferred bytes | Browser DevTools, HAR, request logs |
| Bundle | Total and per-chunk size (raw and gzip) | Build output, bundle analyzer |
| Build | Build duration | `measure.py` around the build command (clean cache vs warm cache: state which) |

## Using measure.py

```
python <skill-dir>/scripts/measure.py run --name before --runs 10 --warmup 2 --output .optimizeit/before.json -- <command> [args...]
```

- Everything after `--` is the command to run (no shell; use `--shell` if you need pipes or shell syntax).
- `--cwd <dir>` sets the working directory.
- `--timeout <seconds>` stops runaway runs.
- A non-zero exit code fails the measurement unless `--allow-failure` is given (a failing command is not a valid benchmark).
- Records per-run wall time and peak memory, plus min/median/mean/stdev/p95.

Peak memory is measured for the direct child process. If the command is a wrapper (`npm run`, `npx`, shell scripts), the real work may happen in a grandchild process; then run the underlying command directly (e.g. `node script.js` instead of `npm run bench`), or treat the memory figure as approximate.

Compare:

```
python <skill-dir>/scripts/measure.py compare .optimizeit/before.json .optimizeit/after.json
```

The comparison prints a Markdown table and flags differences that fall within noise. It also warns when the two measurements used different commands.

## Writing a Benchmark Harness

When no runnable entry point isolates the slow code, write a small harness **in a scratch location** (or in `.optimizeit/` if the user agrees):

```python
# .optimizeit/bench_dedupe.py — calls the real function with realistic input
import random, sys
sys.path.insert(0, ".")
from app.utils import dedupe_orders  # the function under test

random.seed(42)  # fixed seed: identical input before and after
orders = [{"id": random.randint(1, 50_000)} for _ in range(100_000)]
dedupe_orders(orders)
```

Then measure the harness with `measure.py`. Requirements:
- Fixed seed / fixed input file, so before and after use identical data.
- Realistic data size (ask the user or infer from production hints; state your assumption).
- Calls the real code, not a copy.

## Behavior Equivalence Check

Pair each benchmark with an equivalence check: run the old and new implementation on the same inputs (including edge cases: empty, one element, duplicates, unicode, very large, invalid) and assert identical outputs and errors. Keep the old implementation available (git) until the check passes.

## HTTP Load Tests

- Run against a local or staging instance only; never against production or third-party services without explicit permission.
- Fix: concurrency, duration, request mix, payloads, warm-up period.
- Report p50/p95/p99 latency, requests/sec, error rate, and the exact command.

## Reporting Measurements

Always include:
- The exact command(s)
- Environment: OS, CPU, runtime version, build mode
- Number of runs and warm-ups
- Median and spread (stdev or p95)
- Whether the difference exceeds noise

Example (values illustrative only; never copy them):

| Metric | Before | After | Change | Significant? |
|---|---:|---:|---:|---|
| Wall time (median) | 4.20 s | 2.10 s | −50.0% | Yes |
| Peak memory | 450 MB | 310 MB | −31.1% | Yes |

When nothing could be measured:

| Metric | Before | After | Change |
|---|---:|---:|---:|
| API response time | not measured | not measured | — |

> Reason: the service depends on a database that is not available in this environment.
