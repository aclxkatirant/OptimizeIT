# Analysis Checklist (Phase 2)

This list tells you **where to look**. A match is not a problem by itself. For every match, answer three questions:

1. **Is it on a hot path?** Per request, inside a loop, per render, at startup?
2. **How big is the data?** What is the realistic production n?
3. **Is the impact measurable?** Does a profile or measurement show it, or is it theoretical?

Without answers, the finding stays an "unverified suspicion".

## Profile First

Before reading code line by line, profile when you can:

| Need | Method |
|---|---|
| CPU hot spots | Sampling profiler (flame graph) |
| Memory growth | Two heap snapshots taken apart in time, then diff |
| Slow queries | Query log with durations, `EXPLAIN (ANALYZE)` |
| Slow requests | Per-request timing logs, APM/traces, `Server-Timing` headers |
| Startup time | Module load timings, import chain |
| Bundle size | Bundle analyzer with source maps |

Language-specific tools: `languages-and-frameworks.md`.

## 1. Algorithms and Computation

- [ ] **Nested loops / O(n²) or worse:** linear search (`includes`, `indexOf`, `x in list`, `find`) inside a loop → Set/Map/dict for O(1) lookup.
- [ ] **Repeated computation:** loop-invariant expressions, pure functions called repeatedly with the same input → hoist out of the loop, memoize.
- [ ] **Unnecessary sorting:** full sort only to get min/max/top-k → single pass or heap.
- [ ] **Repeated string concatenation:** building large strings with `+=` in a loop (quadratic in some runtimes) → builder/join.
- [ ] **Regex:** compiled on every iteration; patterns at risk of catastrophic backtracking.
- [ ] **Wrong data structure:** array with frequent front insert/delete, list for frequent membership tests.
- [ ] **Unnecessary copying:** spreading arrays/objects in loops, deep copies of large structures, needless `slice()`/`list()`.
- [ ] **Missing early exit:** loops that continue after the result is found.

## 2. Memory

- [ ] **Unbounded growth:** global maps/lists that only ever grow (caches, sessions, subscriber lists).
- [ ] **Listeners/timers never removed:** `addEventListener`, `setInterval`, `on(...)`, subscriptions without teardown.
- [ ] **Closure retention:** long-lived callbacks holding large objects.
- [ ] **Loading everything into memory:** reading a whole large file/result set → streams, pagination, iterators/generators.
- [ ] **Excess allocation:** temporary objects/closures/regexes created in hot loops.
- [ ] **Resource leaks:** files, sockets, DB connections, cursors, transactions not closed.

## 3. I/O and Concurrency

- [ ] **Blocking I/O:** `readFileSync`, `time.sleep`, synchronous HTTP on a server path; blocking calls inside an async framework.
- [ ] **Sequential independent work:** independent `await`s in sequence → `Promise.all` / `asyncio.gather` / errgroup, with bounded concurrency.
- [ ] **Unbounded concurrency:** thousands of parallel requests → pool/semaphore.
- [ ] **Await misuse:** `await` in a loop when parallelizable; a missing `await` (race, unhandled rejection).
- [ ] **CPU-heavy work on the event loop:** large JSON parsing, crypto, image processing in Node/asyncio → worker/thread/process.
- [ ] **File I/O:** unbuffered small reads/writes, reading the same file repeatedly, unnecessary `fsync`.

## 4. Database

Details: `database.md`.

- [ ] Queries inside loops (N+1)
- [ ] Missing indexes on filter/sort/join columns
- [ ] `SELECT *`, fetching unused columns, large BLOB/TEXT
- [ ] Unbounded queries (no LIMIT), deep OFFSET pagination
- [ ] Unnecessary or overly long transactions
- [ ] No connection pool, mis-sized pool, a new connection per request

## 5. Network and APIs

- [ ] **Duplicate requests:** the same data fetched multiple times (per render, per loop iteration).
- [ ] **Single calls where a batch API exists.**
- [ ] **Over-fetching:** returning unused fields, unpaginated list endpoints.
- [ ] **Compression and cache headers:** gzip/brotli, `Cache-Control`, `ETag`.
- [ ] **Connection reuse:** a new HTTP client / TLS handshake per request (no keep-alive).
- [ ] **Missing timeouts:** external calls that can wait forever (stability issue).

## 6. Serialization and Logging

- [ ] Repeated `JSON.stringify`/`parse` of the same data; JSON round-trips used as deep copy.
- [ ] Verbose (debug) logging on hot paths; expensive message construction even when the level is disabled.
- [ ] Synchronous log writes under high traffic.

## 7. Caching

- [ ] Expensive, frequently read, rarely changing data with no cache?
- [ ] Existing cache: size bound, TTL, invalidation? Is the hit rate measured?
- [ ] Does the cache key separate per-user/per-tenant data correctly? (Security!)
- [ ] Cache stampede risk.

## 8. Startup and Dependencies

- [ ] Heavy modules loaded at startup but rarely used → lazy loading.
- [ ] Synchronous network/DB calls or unnecessary warm-up work at startup.
- [ ] Unused dependencies (declared in the manifest, never imported).
- [ ] A heavy dependency used for a trivial task.
- [ ] Multiple libraries doing the same job (two date libraries, two HTTP clients).

> Removing or replacing a dependency risks behavior and API changes; report it as a recommendation and do not apply it without approval.

## 9. Frontend

Details: `frontend.md`. Unnecessary re-renders, bundle size, unoptimized images, layout thrashing, render-blocking scripts, lazy loading and code splitting opportunities.

## 10. Build and Tooling

- [ ] Build cache disabled, no incremental compilation.
- [ ] Large unneeded files pulled into the bundle or compilation.
- [ ] CI reinstalling all dependencies from scratch on every run.

## Finding Assessment Table

| Question | If yes |
|---|---|
| Does a profile/measurement point here? | Priority may rise (HIGH/CRITICAL candidate) |
| On a hot path with large n? | At least MEDIUM |
| Only theoretical, small data? | LOW or INFORMATIONAL |
| Does the fix change behavior, API or schema? | Approval required |
| Does the fix badly hurt readability for a small gain? | Do not implement |
