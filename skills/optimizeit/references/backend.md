# Backend Optimization

**Rule:** Optimize for real production workloads, not just synthetic benchmarks. The API contract (paths, status codes, response shape, error behavior) does not change without authorization.

## Request Lifecycle

Trace one slow request end to end and note where the time goes:

```
network → load balancer → middleware chain → routing → auth → validation
       → business logic → DB / cache / external calls → serialization → response
```

Instrument with what the project already has (APM, OpenTelemetry, structured logs). Otherwise add temporary timing (and remove it afterwards).

## Middleware

- Middleware running on every request that only some routes need (body parsing on GET, auth on public assets, heavy logging) → scope to routes.
- Expensive middleware ordered before cheap rejections (rate limiting, 404 for static) → reorder **only** if the semantics stay the same (auth and security order matters!).
- Sessions loaded from a store on requests that do not use them.

## Event Loop Blocking (Node.js, Python asyncio, etc.)

- Synchronous filesystem/crypto/compression calls in handlers (`fs.*Sync`, `crypto.pbkdf2Sync`, `zlib.*Sync`).
- Large `JSON.parse`/`JSON.stringify` on big payloads.
- CPU-heavy loops (report generation, image processing) → worker threads / process pool / job queue.
- In Python asyncio: blocking libraries (`requests`, sync DB drivers) inside `async def` → async client or `run_in_executor`/`asyncio.to_thread`.
- Detection: event loop lag metrics (`perf_hooks.monitorEventLoopDelay`), asyncio debug mode (`PYTHONASYNCIODEBUG=1`, slow callback warnings).

## Concurrency and Workers

- Independent I/O calls done sequentially → parallel, with bounded concurrency.
- Worker/process count vs CPU count (gunicorn/uvicorn workers, PM2 cluster, PHP-FPM `pm.max_children`, thread pools). Changing these is configuration: recommend with justification, get approval.
- Thread pool starvation (.NET sync-over-async, `.Result`/`.Wait()`; Java blocking calls in reactive code).
- Lock contention: coarse locks around slow operations → narrow critical sections.

## External Calls

- No connection reuse → shared HTTP client with keep-alive (one `HttpClient`/`IHttpClientFactory`, one `requests.Session`/`httpx.Client`, an `http.Agent` with keepAlive).
- No timeouts → add timeouts (behavior change if callers depended on long waits: note it).
- Retries without backoff/jitter → retry storms.
- Repeated calls for the same data within one request → per-request memoization.

## Serialization

- Serializing large ORM objects with lazy relations (triggers N+1 during serialization).
- Returning fields the client does not use (response shape is a contract: trimming fields needs approval).
- Pretty-printing JSON in production.
- Faster serializers (orjson, System.Text.Json source generators, fast-json-stringify) are dependency/behavior changes → recommend, check output equivalence (key order, number and date formats).

## Caching

Layers, from cheapest: in-process memo → in-process LRU → shared cache (Redis/Memcached) → HTTP cache (`Cache-Control`, `ETag`, CDN).

Every cache must define: key (including tenant/user/locale/permissions where relevant), TTL, size bound, invalidation trigger, stampede protection, behavior on cache failure.

Never cache: authorization decisions across users, responses containing per-user data under a shared key.

## Resource Cleanup and Connections

- Files, sockets, DB connections, streams closed on all paths (`try/finally`, `with`, `using`, `defer`).
- Long-lived processes: unbounded in-memory maps, growing listener lists, timers never cleared.
- Graceful shutdown: in-flight requests and pool connections drained.

## Background Jobs

- Slow non-critical work done inline in requests (emails, thumbnails, webhooks) → job queue. Changes response timing and failure semantics → approval.
- Jobs loading whole tables into memory → batches/streams.
- Polling loops with tight intervals → longer intervals or event-driven triggers.
- Missing idempotency when introducing retries.

## Logging

- Debug-level logging on hot paths in production.
- Synchronous log transports under load.
- Logging whole request/response bodies (also a privacy risk).

## Startup

- Heavy imports/initialization not needed for the first request → lazy initialization.
- Sequential independent startup steps (connecting to DB, cache, broker) → parallel.
- Migrations or seeding run on every startup.

## Load Testing

Use what is installed, or ask before installing: `autocannon` (Node), `wrk`, `hey`, `k6`, `ab`, `locust`, `vegeta`.

Record: concurrency, duration, request mix, p50/p95/p99 latency, throughput, error rate. Same parameters before and after. Never load test production or third-party services without explicit permission.
