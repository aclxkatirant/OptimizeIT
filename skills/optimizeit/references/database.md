# Database Optimization

## Golden Rules

- **Never apply destructive migrations automatically** (DROP TABLE/COLUMN, type changes, data rewrites, renames). Explain them and get approval.
- Adding an index is a schema change too: explain the write cost, disk usage and lock behavior; get approval. On large tables, prefer online creation (`CREATE INDEX CONCURRENTLY` in PostgreSQL, `ALGORITHM=INPLACE, LOCK=NONE` in MySQL).
- Never replace parameterized queries with string concatenation (SQL injection).
- When changing a query, the result set (rows, order, NULL handling) must stay the same.

## Finding the Problem

| Database | Slow query source | Plan |
|---|---|---|
| PostgreSQL | `pg_stat_statements`, `log_min_duration_statement` | `EXPLAIN (ANALYZE, BUFFERS)` |
| MySQL/MariaDB | slow query log, `performance_schema` | `EXPLAIN ANALYZE` (8.0.18+) |
| SQLite | timing around calls | `EXPLAIN QUERY PLAN` |
| SQL Server | Query Store, DMVs | Actual Execution Plan |
| MongoDB | profiler (`db.setProfilingLevel`) | `.explain("executionStats")` |

> `EXPLAIN ANALYZE` **executes** the query. Do not run it on write queries (INSERT/UPDATE/DELETE) against real data; use a transaction + ROLLBACK or a copy.

ORM query logging: Django `connection.queries` / django-debug-toolbar, SQLAlchemy `echo=True`, Laravel `DB::enableQueryLog()` / Telescope, Rails logs, Prisma `log: ['query']`, TypeORM `logging: true`, EF Core `LogTo`, Hibernate `show_sql` + statistics.

## N+1 Queries

**Symptom:** a list query followed by one query per row.

```python
# BAD: 1 + N queries
for order in Order.objects.all():
    print(order.customer.name)

# GOOD: 1 query with a JOIN
for order in Order.objects.select_related("customer"):
    print(order.customer.name)
```

| ORM | Fix |
|---|---|
| Django | `select_related` (FK/1-1), `prefetch_related` (M2M/reverse FK) |
| SQLAlchemy | `joinedload`, `selectinload` |
| Laravel Eloquent | `with()`, `load()`; detect with `Model::preventLazyLoading()` |
| Rails ActiveRecord | `includes`, `preload`, `eager_load`; the `bullet` gem |
| Prisma | `include` / `select`, or `findMany` + `in` |
| TypeORM | `relations`, `leftJoinAndSelect` |
| EF Core | `Include`, `ThenInclude`, `AsSplitQuery` |
| Hibernate/JPA | `JOIN FETCH`, `@EntityGraph`, batch fetching |
| GraphQL | DataLoader (batching + per-request caching) |

**Validation:** count queries before and after (query log or a test that asserts the query count).

## Indexes

Index candidates:
- Columns in `WHERE`, `JOIN ... ON`, `ORDER BY`, `GROUP BY`.
- Composite index column order: equality filters first, then range/sort columns.
- Covering indexes (`INCLUDE` / all needed columns) to avoid table lookups.

Things that prevent index use:
- Wrapping the column in a function (`WHERE LOWER(email) = ...`) → expression index or normalized column.
- Leading wildcard `LIKE '%x'` → full-text/trigram index.
- Implicit type conversion (comparing a string column to a number).
- Using a composite index without its leading column.

Redundant indexes: an index that is a prefix of another, or never used (`pg_stat_user_indexes.idx_scan = 0`). They slow writes. Report removals as recommendations; removal is a schema change and needs approval.

## Unnecessary Data Retrieval

- `SELECT *` → only the needed columns (ORM: `only()`, `values()`, `select`, projections).
- Large TEXT/BLOB columns in list queries → load them separately.
- Fetching rows only to count them → `COUNT(*)` / `EXISTS`.
- Filtering/aggregating in application code → `WHERE`, `GROUP BY`, `SUM` in the database.

## Pagination

- `OFFSET 100000` reads and discards 100,000 rows. → Keyset (cursor) pagination: `WHERE (created_at, id) < (?, ?) ORDER BY created_at DESC, id DESC LIMIT 50`.
- Changing pagination style can change API behavior (page numbers → cursor); needs approval.

## Round Trips and Batching

- Inserting/updating inside a loop → bulk insert (`bulk_create`, `insertMany`, multi-row `INSERT ... VALUES`, `COPY`).
- Many lookups by id → a single `WHERE id IN (...)` (chunk very large lists).
- Several independent queries → parallel where the driver and pool allow it, or a single combined query.

## Transactions

- Transactions too long: no network/file I/O or user waits inside a transaction; locks are held.
- Many tiny transactions: each single-row write in its own transaction → batching (consistency semantics must stay the same).
- Do not change the isolation level without approval; it affects correctness.

## Connection Pools

- A new connection per request → pool.
- Pool size: more is not better. The database's `max_connections` divided by the number of app instances is the ceiling; a common starting point is a small multiple of CPU cores.
- Serverless: use an external pooler (PgBouncer, RDS Proxy, etc.).
- Are connections released (`finally`/`using`/`with`/`defer`)? Leaks show up as pool exhaustion.

## Caching

- Rarely changing reference data (settings, country lists) → application cache.
- Query cache invalidation must happen on writes; stale data is a correctness bug.
- Per-user data must never be shared across users through a shared cache key.

## Reporting Schema Changes

Use this format in the report for every schema change:

```markdown
**Proposed schema change (awaiting approval):**
- SQL: `CREATE INDEX CONCURRENTLY idx_orders_customer_created ON orders (customer_id, created_at DESC);`
- Purpose: OPT-3 — avoid the full table scan in the order listing query.
- Expected effect: <EXPLAIN plan before/after, if available>
- Cost: extra write overhead on inserts, ~<size> disk, build time on a large table.
- Lock behavior: CONCURRENTLY does not block writes; cannot run inside a transaction.
- Rollback: `DROP INDEX CONCURRENTLY idx_orders_customer_created;`
- Destructive: No
```
