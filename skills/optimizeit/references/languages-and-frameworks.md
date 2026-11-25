# Languages and Frameworks

Read the runtime and framework versions from manifests/lockfiles before applying anything here. Some advice depends on version (for example, React Compiler auto-memoization, Python 3.11+ speedups, .NET source generators).

## Profilers by Stack

| Stack | CPU profiling | Memory | Notes |
|---|---|---|---|
| Node.js | `node --cpu-prof`, `--prof`, `0x`, `clinic flame` | `--heap-prof`, `--inspect` heap snapshots, `clinic heapprofiler` | `clinic doctor` for event loop issues |
| Browser JS | DevTools Performance | DevTools Memory | Production build only |
| Python | `cProfile` + `snakeviz`, `py-spy record` (sampling, no code change) | `tracemalloc`, `memray` | `python -X importtime` for startup |
| PHP | Xdebug profiler, Blackfire, SPX | `memory_get_peak_usage()` | Check OPcache is enabled |
| Java/Kotlin (JVM) | async-profiler, JFR (`-XX:+FlightRecorder`), VisualVM | heap dump + Eclipse MAT | Warm-up matters: use JMH for microbenchmarks |
| C# / .NET | `dotnet-trace`, `dotnet-counters`, PerfView | `dotnet-gcdump`, `dotnet-dump` | BenchmarkDotNet for microbenchmarks |
| Go | `pprof` (`net/http/pprof`, `go test -cpuprofile`) | `go test -memprofile`, heap pprof | `go test -bench . -benchmem` |
| Rust | `cargo flamegraph`, `perf` | `heaptrack`, `dhat` | Always measure `--release` |
| C/C++ | `perf`, VTune, `gprof` | Valgrind massif, heaptrack, ASan for leaks | Compare with the same optimization flags |
| Swift | Instruments (Time Profiler) | Instruments (Allocations, Leaks) | Release configuration |
| Ruby | `stackprof`, `rbspy` | `memory_profiler`, `derailed_benchmarks` | |
| SQL | `EXPLAIN (ANALYZE)` | — | See `database.md` |

Do not install profilers or add dependencies to the project without asking. Prefer tools already present or tools that run without changing the project (for example `py-spy`, `node --cpu-prof`).

## JavaScript / TypeScript / Node.js

- `array.includes`/`indexOf`/`find` inside loops → `Set`/`Map`.
- `await` inside `for` loops for independent work → `Promise.all` with a concurrency limit.
- `JSON.parse(JSON.stringify(x))` for cloning → `structuredClone` (Node 17+) or targeted copies.
- `Array.prototype.reduce` with spread accumulators (`{...acc, [k]: v}`) → O(n²); mutate a local accumulator.
- `fs.*Sync` on request paths.
- `delete obj.prop` on hot objects; megamorphic objects with changing shapes in hot code.
- Unbounded `Map` caches → LRU with a size bound.
- Startup: top-level imports of heavy modules → dynamic `import()` where appropriate.
- TypeScript: slow builds → `incremental`, `skipLibCheck`, project references (build config changes need approval).

## Python

- Membership tests on lists inside loops → `set`.
- String building with `+=` in loops → `"".join(...)`.
- Repeated attribute/global lookups in very hot loops → local variable (only if the profiler shows it).
- Pure-Python numeric loops over large arrays → NumPy/pandas vectorization (if already a dependency).
- `pandas`: `iterrows`/`apply` row-wise → vectorized operations; avoid repeated `concat` in loops.
- `functools.lru_cache`/`cache` for pure functions (watch memory and mutable arguments).
- Django: `select_related`/`prefetch_related`, `only()`/`values()`, `exists()` instead of `count()`/truthiness on querysets, `iterator()` for large querysets, `bulk_create`/`bulk_update`.
- FastAPI: blocking calls inside `async def` endpoints; use `def` endpoints (run in a threadpool) or async libraries; reuse a single `httpx.AsyncClient`.
- Startup: `python -X importtime` to find slow imports.

## PHP / Laravel

- Verify OPcache (and JIT where relevant) in production config — recommend, do not change server config without approval.
- Eloquent N+1 → `with()`; `Model::preventLazyLoading()` in development to detect.
- `->get()` on large tables → `chunk()`, `lazy()`, `cursor()`.
- `config:cache`, `route:cache`, `view:cache`, `composer install --optimize-autoloader --no-dev` in deployment.
- Queries inside Blade loops.

## Java / Kotlin / Spring

- `String` concatenation in loops → `StringBuilder`.
- Boxing in hot loops (`List<Integer>`) → primitive arrays or specialized collections.
- JPA N+1 → `JOIN FETCH`, `@EntityGraph`, `hibernate.default_batch_fetch_size`.
- `@Transactional` boundaries too wide; open-session-in-view causing lazy loads in views.
- Connection pool (HikariCP) sizing; thread pool sizing for blocking I/O.
- Reflection-heavy startup → lazy initialization (`spring.main.lazy-initialization` changes behavior: approval).

## C# / .NET / ASP.NET Core

- Sync-over-async (`.Result`, `.Wait()`) → `await` all the way.
- New `HttpClient` per request → `IHttpClientFactory`.
- EF Core: `AsNoTracking` for read-only queries, `Include` for N+1, projections with `Select`, compiled queries for very hot paths, `AsSplitQuery` for cartesian explosion.
- LINQ in hot paths: multiple enumeration of `IEnumerable`, `Count()` vs `Any()`.
- Allocations: `Span<T>`, `ArrayPool<T>`, `StringBuilder` (only where profiling shows allocation pressure).
- Response compression and output caching middleware.

## Go

- Slices/maps grown in loops without capacity → `make([]T, 0, n)`.
- String concatenation in loops → `strings.Builder`.
- Goroutine leaks: goroutines blocked forever on channels; use `context` cancellation.
- `sync.Pool` for hot, short-lived allocations (only when the profiler shows GC pressure).
- `defer` in very tight loops (older Go versions).
- Mutex contention → sharding or `sync.RWMutex` where reads dominate.

## Rust

- Unnecessary `.clone()` / `.to_string()` / `.collect()` in hot paths → borrows, iterators.
- `Vec` without `with_capacity` when the size is known.
- Debug vs release builds: never benchmark debug.
- Blocking calls inside async runtimes (Tokio) → `spawn_blocking`.
- Lock contention on `Mutex<HashMap>` → sharded maps or `RwLock`.

## C / C++

- Copies of large objects by value → `const&`, move semantics.
- `std::endl` in hot output loops (flushes) → `'\n'`.
- `std::map` where `std::unordered_map` fits; `reserve()` on vectors.
- Cache-unfriendly data layouts (arrays of pointers) in hot loops.
- Allocation in tight loops → reuse buffers.
- Compare with the same compiler and optimization flags; changing flags is a build change (approval).

## Swift / Kotlin (mobile)

- Main-thread work: I/O, JSON decoding, image decoding → background queue/coroutine dispatcher.
- Large images decoded at full size → downsample to display size.
- Retain cycles (Swift closures capturing `self` strongly; Android `Context` leaks).
- List performance: cell/view reuse, diffing (`DiffableDataSource`, `DiffUtil`), stable IDs.

## SQL

See `database.md`.

## Frontend Frameworks (React, Next.js, Vue, Angular, Svelte)

See `frontend.md`.

## Backend Frameworks (Express, NestJS, Django, FastAPI, Laravel, ASP.NET Core, Spring)

See `backend.md`, plus the language section above.
