#!/usr/bin/env python3
"""OptimizeIT project discovery.

Scans a project directory and reports languages, frameworks, package managers,
build systems, entry points, database technologies, external services,
test/lint/typecheck/build commands and the largest source files.

The output is a starting point for Phase 1 (Discovery). Always verify it by
reading the manifests and entry points yourself.

Usage:
    python discover.py <project-dir> [--json] [--top N]

Standard library only. Python 3.8+.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict

IGNORED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "bower_components", "vendor", "venv", ".venv",
    "env", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "dist",
    "build", "out", "target", "obj", ".next", ".nuxt", ".svelte-kit", ".angular",
    ".turbo", ".cache", ".parcel-cache", "coverage", ".nyc_output", ".idea", ".vscode",
    ".gradle", "Pods", "DerivedData", ".dart_tool", ".optimizeit", ".terraform",
    "bootstrap/cache", "storage/framework",
}

LANGUAGES = {
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript (JSX)",
    ".ts": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript", ".tsx": "TypeScript (TSX)",
    ".py": "Python", ".pyx": "Cython", ".php": "PHP", ".java": "Java", ".kt": "Kotlin",
    ".kts": "Kotlin", ".scala": "Scala", ".groovy": "Groovy", ".cs": "C#", ".fs": "F#",
    ".vb": "Visual Basic", ".c": "C", ".h": "C/C++ header", ".cc": "C++", ".cpp": "C++",
    ".cxx": "C++", ".hpp": "C++", ".hh": "C++", ".go": "Go", ".rs": "Rust", ".swift": "Swift",
    ".m": "Objective-C", ".mm": "Objective-C++", ".rb": "Ruby", ".ex": "Elixir",
    ".exs": "Elixir", ".erl": "Erlang", ".dart": "Dart", ".lua": "Lua", ".r": "R",
    ".jl": "Julia", ".sql": "SQL", ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "Sass", ".less": "Less",
    ".sh": "Shell", ".bash": "Shell", ".ps1": "PowerShell", ".zig": "Zig", ".nim": "Nim",
    ".clj": "Clojure", ".hs": "Haskell", ".ml": "OCaml", ".pl": "Perl", ".cshtml": "Razor",
    ".razor": "Razor", ".blade.php": "Blade",
}

# Languages counted as "source" for the largest-files list.
NON_SOURCE = {"HTML", "CSS", "SCSS", "Sass", "Less", "SQL", "Shell", "PowerShell"}

# Dependency name (lowercase) -> (category, label)
KNOWN_DEPS = {
    # JavaScript / TypeScript frameworks
    "react": ("framework", "React"), "react-dom": ("framework", "React DOM"),
    "next": ("framework", "Next.js"), "vue": ("framework", "Vue"), "nuxt": ("framework", "Nuxt"),
    "@angular/core": ("framework", "Angular"), "svelte": ("framework", "Svelte"),
    "@sveltejs/kit": ("framework", "SvelteKit"), "solid-js": ("framework", "SolidJS"),
    "astro": ("framework", "Astro"), "@remix-run/react": ("framework", "Remix"),
    "express": ("framework", "Express"), "@nestjs/core": ("framework", "NestJS"),
    "fastify": ("framework", "Fastify"), "koa": ("framework", "Koa"), "hono": ("framework", "Hono"),
    "@hapi/hapi": ("framework", "hapi"), "electron": ("framework", "Electron"),
    "react-native": ("framework", "React Native"), "expo": ("framework", "Expo"),
    "@reduxjs/toolkit": ("library", "Redux Toolkit"), "redux": ("library", "Redux"),
    "zustand": ("library", "Zustand"), "mobx": ("library", "MobX"), "pinia": ("library", "Pinia"),
    "@tanstack/react-query": ("library", "TanStack Query"), "swr": ("library", "SWR"),
    "@apollo/client": ("library", "Apollo Client"), "graphql": ("library", "GraphQL"),
    "lodash": ("library", "lodash"), "moment": ("library", "moment.js"),
    "rxjs": ("library", "RxJS"), "socket.io": ("library", "Socket.IO"),
    # JS build tools
    "vite": ("build", "Vite"), "webpack": ("build", "webpack"), "rollup": ("build", "Rollup"),
    "esbuild": ("build", "esbuild"), "parcel": ("build", "Parcel"), "turbo": ("build", "Turborepo"),
    "typescript": ("build", "TypeScript compiler"), "@swc/core": ("build", "SWC"),
    # JS test/lint
    "jest": ("test", "Jest"), "vitest": ("test", "Vitest"), "mocha": ("test", "Mocha"),
    "@playwright/test": ("test", "Playwright"), "cypress": ("test", "Cypress"),
    "eslint": ("lint", "ESLint"), "@biomejs/biome": ("lint", "Biome"), "prettier": ("lint", "Prettier"),
    # JS databases / ORMs
    "prisma": ("database", "Prisma ORM"), "@prisma/client": ("database", "Prisma ORM"),
    "typeorm": ("database", "TypeORM"), "sequelize": ("database", "Sequelize"),
    "mongoose": ("database", "MongoDB (Mongoose)"), "mongodb": ("database", "MongoDB"),
    "drizzle-orm": ("database", "Drizzle ORM"), "knex": ("database", "Knex"),
    "pg": ("database", "PostgreSQL (pg)"), "postgres": ("database", "PostgreSQL"),
    "mysql": ("database", "MySQL"), "mysql2": ("database", "MySQL"),
    "better-sqlite3": ("database", "SQLite"), "sqlite3": ("database", "SQLite"),
    "redis": ("database", "Redis"), "ioredis": ("database", "Redis"),
    "@supabase/supabase-js": ("service", "Supabase"), "firebase": ("service", "Firebase"),
    "firebase-admin": ("service", "Firebase"),
    # Python
    "django": ("framework", "Django"), "djangorestframework": ("framework", "Django REST Framework"),
    "flask": ("framework", "Flask"), "fastapi": ("framework", "FastAPI"),
    "starlette": ("framework", "Starlette"), "tornado": ("framework", "Tornado"),
    "aiohttp": ("framework", "aiohttp"), "celery": ("library", "Celery"),
    "pandas": ("library", "pandas"), "numpy": ("library", "NumPy"), "polars": ("library", "Polars"),
    "pydantic": ("library", "Pydantic"), "uvicorn": ("library", "Uvicorn"),
    "gunicorn": ("library", "Gunicorn"), "requests": ("library", "requests"), "httpx": ("library", "httpx"),
    "sqlalchemy": ("database", "SQLAlchemy"), "psycopg2": ("database", "PostgreSQL (psycopg2)"),
    "psycopg2-binary": ("database", "PostgreSQL (psycopg2)"), "psycopg": ("database", "PostgreSQL (psycopg)"),
    "asyncpg": ("database", "PostgreSQL (asyncpg)"), "pymysql": ("database", "MySQL"),
    "mysqlclient": ("database", "MySQL"), "pymongo": ("database", "MongoDB"),
    "motor": ("database", "MongoDB (motor)"), "peewee": ("database", "Peewee ORM"),
    "tortoise-orm": ("database", "Tortoise ORM"), "pytest": ("test", "pytest"),
    "ruff": ("lint", "Ruff"), "flake8": ("lint", "flake8"), "pylint": ("lint", "Pylint"),
    "mypy": ("lint", "mypy"), "pyright": ("lint", "Pyright"), "black": ("lint", "Black"),
    # PHP
    "laravel/framework": ("framework", "Laravel"), "symfony/framework-bundle": ("framework", "Symfony"),
    "symfony/http-kernel": ("framework", "Symfony"), "slim/slim": ("framework", "Slim"),
    "doctrine/orm": ("database", "Doctrine ORM"), "phpunit/phpunit": ("test", "PHPUnit"),
    "pestphp/pest": ("test", "Pest"), "phpstan/phpstan": ("lint", "PHPStan"),
    "predis/predis": ("database", "Redis"),
    # Ruby
    "rails": ("framework", "Ruby on Rails"), "sinatra": ("framework", "Sinatra"),
    "sidekiq": ("library", "Sidekiq"), "rspec": ("test", "RSpec"), "pg_ruby": ("database", "PostgreSQL"),
    # Go
    "github.com/gin-gonic/gin": ("framework", "Gin"), "github.com/labstack/echo/v4": ("framework", "Echo"),
    "github.com/gofiber/fiber/v2": ("framework", "Fiber"), "github.com/go-chi/chi/v5": ("framework", "chi"),
    "gorm.io/gorm": ("database", "GORM"), "github.com/jackc/pgx/v5": ("database", "PostgreSQL (pgx)"),
    "github.com/lib/pq": ("database", "PostgreSQL (lib/pq)"),
    "github.com/go-sql-driver/mysql": ("database", "MySQL"),
    "go.mongodb.org/mongo-driver": ("database", "MongoDB"),
    "github.com/redis/go-redis/v9": ("database", "Redis"),
    # Rust
    "actix-web": ("framework", "Actix Web"), "axum": ("framework", "Axum"), "rocket": ("framework", "Rocket"),
    "tokio": ("library", "Tokio"), "diesel": ("database", "Diesel"), "sqlx": ("database", "SQLx"),
    "sea-orm": ("database", "SeaORM"), "serde": ("library", "serde"),
    # .NET (PackageReference names)
    "microsoft.entityframeworkcore": ("database", "Entity Framework Core"),
    "npgsql.entityframeworkcore.postgresql": ("database", "PostgreSQL (EF Core)"),
    "microsoft.entityframeworkcore.sqlserver": ("database", "SQL Server (EF Core)"),
    "dapper": ("database", "Dapper"), "stackexchange.redis": ("database", "Redis"),
    "xunit": ("test", "xUnit"), "nunit": ("test", "NUnit"), "mstest.testframework": ("test", "MSTest"),
    # External services (any ecosystem)
    "stripe": ("service", "Stripe"), "aws-sdk": ("service", "AWS SDK"), "boto3": ("service", "AWS (boto3)"),
    "@sentry/node": ("service", "Sentry"), "@sentry/react": ("service", "Sentry"),
    "sentry-sdk": ("service", "Sentry"), "openai": ("service", "OpenAI API"),
    "@anthropic-ai/sdk": ("service", "Anthropic API"), "anthropic": ("service", "Anthropic API"),
    "twilio": ("service", "Twilio"), "@sendgrid/mail": ("service", "SendGrid"),
    "kafkajs": ("service", "Kafka"), "amqplib": ("service", "RabbitMQ"), "bullmq": ("service", "BullMQ (Redis)"),
    "@elastic/elasticsearch": ("service", "Elasticsearch"), "elasticsearch": ("service", "Elasticsearch"),
}

PREFIX_DEPS = [
    ("@aws-sdk/", ("service", "AWS SDK v3")),
    ("@google-cloud/", ("service", "Google Cloud")),
    ("@azure/", ("service", "Azure SDK")),
    ("@opentelemetry/", ("library", "OpenTelemetry")),
    ("org.springframework.boot", ("framework", "Spring Boot")),
    ("microsoft.aspnetcore", ("framework", "ASP.NET Core")),
]

LOCKFILES = {
    "package-lock.json": "npm", "yarn.lock": "Yarn", "pnpm-lock.yaml": "pnpm", "bun.lockb": "Bun",
    "bun.lock": "Bun", "poetry.lock": "Poetry", "uv.lock": "uv", "Pipfile.lock": "Pipenv",
    "pdm.lock": "PDM", "composer.lock": "Composer", "Gemfile.lock": "Bundler", "Cargo.lock": "Cargo",
    "go.sum": "Go modules", "packages.lock.json": "NuGet", "pubspec.lock": "Pub (Dart)",
    "mix.lock": "Mix (Elixir)", "Package.resolved": "Swift Package Manager",
}

BUILD_FILES = {
    "package.json": "npm-style package.json", "pyproject.toml": "pyproject.toml",
    "setup.py": "setuptools", "requirements.txt": "pip requirements", "Pipfile": "Pipenv",
    "composer.json": "Composer", "pom.xml": "Maven", "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle (Kotlin DSL)", "go.mod": "Go modules", "Cargo.toml": "Cargo",
    "Gemfile": "Bundler", "CMakeLists.txt": "CMake", "Makefile": "Make", "meson.build": "Meson",
    "Package.swift": "Swift Package Manager", "pubspec.yaml": "Pub (Dart)", "mix.exs": "Mix",
    "Dockerfile": "Docker", "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose", "compose.yml": "Docker Compose",
    "compose.yaml": "Docker Compose", "turbo.json": "Turborepo", "nx.json": "Nx",
    "lerna.json": "Lerna", "angular.json": "Angular CLI", "vite.config.ts": "Vite",
    "vite.config.js": "Vite", "webpack.config.js": "webpack", "next.config.js": "Next.js",
    "next.config.mjs": "Next.js", "next.config.ts": "Next.js", "nuxt.config.ts": "Nuxt",
    "tsconfig.json": "TypeScript", "artisan": "Laravel Artisan", "manage.py": "Django manage.py",
}

ENTRY_POINT_NAMES = {
    "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py", "__main__.py", "server.py",
    "server.js", "server.ts", "index.js", "index.ts", "app.js", "app.ts", "main.js", "main.ts",
    "main.go", "main.rs", "lib.rs", "Program.cs", "Startup.cs", "artisan", "index.php",
    "Application.java", "Main.java", "main.kt", "Application.kt", "main.c", "main.cpp",
    "main.swift", "App.swift", "_app.tsx", "_app.jsx", "layout.tsx", "App.tsx", "App.jsx",
    "App.vue", "main.dart", "config.ru",
}

COMPOSE_IMAGES = {
    "postgres": "PostgreSQL", "postgis": "PostgreSQL (PostGIS)", "mysql": "MySQL", "mariadb": "MariaDB",
    "mongo": "MongoDB", "redis": "Redis", "valkey": "Valkey", "memcached": "Memcached",
    "elasticsearch": "Elasticsearch", "opensearch": "OpenSearch", "rabbitmq": "RabbitMQ",
    "kafka": "Kafka", "mssql": "SQL Server", "cassandra": "Cassandra", "clickhouse": "ClickHouse",
    "minio": "MinIO", "nats": "NATS",
}


def read_text(path, limit=2_000_000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def load_json(path):
    try:
        return json.loads(read_text(path))
    except (ValueError, TypeError):
        return None


def count_lines(path):
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def classify(name):
    key = name.lower().strip()
    if key in KNOWN_DEPS:
        return KNOWN_DEPS[key]
    for prefix, value in PREFIX_DEPS:
        if key.startswith(prefix):
            return value
    return None


def language_of(filename):
    lower = filename.lower()
    if lower.endswith(".blade.php"):
        return "Blade"
    if lower.endswith(".d.ts"):
        return None
    if lower.endswith((".min.js", ".min.css", ".bundle.js")):
        return None
    return LANGUAGES.get(os.path.splitext(lower)[1])


class Report:
    def __init__(self, root):
        self.root = root
        self.languages = Counter()
        self.language_lines = Counter()
        self.source_files = []  # (lines, relpath)
        self.manifests = []
        self.build_systems = set()
        self.package_managers = set()
        self.detected = defaultdict(set)  # category -> labels
        self.dependency_counts = {}
        self.entry_points = []
        self.commands = []
        self.notes = []
        self.ci = []
        self.git = {}

    def add(self, category, label, source):
        self.detected[category].add("%s (%s)" % (label, source))

    def add_dep(self, name, source):
        hit = classify(name)
        if hit:
            self.add(hit[0], hit[1], source)

    def add_command(self, kind, command, source):
        entry = {"kind": kind, "command": command, "source": source}
        if entry not in self.commands:
            self.commands.append(entry)


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def js_runner(pm):
    return {"pnpm": "pnpm", "Yarn": "yarn", "Bun": "bun run"}.get(pm, "npm run")


def parse_package_json(report, path, lock_pm):
    data = load_json(path)
    if not isinstance(data, dict):
        return
    source = rel(report.root, path)
    deps = {}
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        if isinstance(data.get(key), dict):
            deps.update(data[key])
    report.dependency_counts[source] = len(deps)
    for name in deps:
        report.add_dep(name, source)
    pm_field = data.get("packageManager")
    pm = lock_pm
    if isinstance(pm_field, str):
        pm = {"pnpm": "pnpm", "yarn": "Yarn", "npm": "npm", "bun": "Bun"}.get(pm_field.split("@")[0], pm)
        report.package_managers.add("%s (packageManager field in %s)" % (pm, source))
    if isinstance(data.get("engines"), dict) and data["engines"].get("node"):
        report.notes.append("Node engine constraint %s (%s)" % (data["engines"]["node"], source))
    runner = js_runner(pm)
    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    kinds = [
        ("test", re.compile(r"^(test|test:unit|unit)$")),
        ("lint", re.compile(r"^lint$")),
        ("typecheck", re.compile(r"^(typecheck|type-check|types|tsc|check-types)$")),
        ("build", re.compile(r"^build$")),
        ("start", re.compile(r"^(start|serve|dev)$")),
        ("benchmark", re.compile(r"^(bench|benchmark)(:.*)?$")),
    ]
    for script_name in scripts:
        for kind, pattern in kinds:
            if pattern.match(script_name):
                prefix = "npm" if (runner == "npm run" and script_name in ("test", "start")) else runner
                cmd = "%s %s" % (prefix, script_name)
                report.add_command(kind, cmd, source)
    for field in ("main", "module"):
        if isinstance(data.get(field), str):
            report.entry_points.append("%s (%s.%s)" % (data[field], source, field))
    if isinstance(data.get("bin"), dict):
        for target in data["bin"].values():
            report.entry_points.append("%s (%s.bin)" % (target, source))
    elif isinstance(data.get("bin"), str):
        report.entry_points.append("%s (%s.bin)" % (data["bin"], source))
    if isinstance(data.get("workspaces"), (list, dict)):
        report.notes.append("Monorepo workspaces declared in %s" % source)


REQ_LINE = re.compile(r"^\s*([A-Za-z0-9_.\-\[\]]+)")


def parse_requirements(report, path):
    source = rel(report.root, path)
    count = 0
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        m = REQ_LINE.match(line)
        if m:
            count += 1
            report.add_dep(re.sub(r"\[.*\]", "", m.group(1)), source)
    report.dependency_counts[source] = count


def parse_pyproject(report, path):
    source = rel(report.root, path)
    text = read_text(path)
    data = None
    try:
        import tomllib  # Python 3.11+
        data = tomllib.loads(text)
    except Exception:
        data = None
    names = set()
    if isinstance(data, dict):
        project = data.get("project", {})
        for spec in project.get("dependencies", []) or []:
            m = REQ_LINE.match(spec)
            if m:
                names.add(re.sub(r"\[.*\]", "", m.group(1)))
        for group in (project.get("optional-dependencies", {}) or {}).values():
            for spec in group:
                m = REQ_LINE.match(spec)
                if m:
                    names.add(re.sub(r"\[.*\]", "", m.group(1)))
        for group in (data.get("dependency-groups", {}) or {}).values():
            for spec in group:
                if isinstance(spec, str):
                    m = REQ_LINE.match(spec)
                    if m:
                        names.add(m.group(1))
        poetry = data.get("tool", {}).get("poetry", {})
        for key in ("dependencies", "dev-dependencies"):
            names.update((poetry.get(key) or {}).keys())
        for grp in (poetry.get("group") or {}).values():
            names.update((grp.get("dependencies") or {}).keys())
        names.discard("python")
        tools = data.get("tool", {})
        if "pytest" in tools:
            report.add_command("test", "pytest", source)
        if "ruff" in tools:
            report.add_command("lint", "ruff check .", source)
        if "mypy" in tools:
            report.add_command("typecheck", "mypy .", source)
        requires = project.get("requires-python")
        if requires:
            report.notes.append("Python requirement %s (%s)" % (requires, source))
    else:
        for m in re.finditer(r'^\s*"?([A-Za-z0-9_.\-]+)\s*[<>=~!"\[]', text, re.M):
            names.add(m.group(1))
    for name in names:
        report.add_dep(name, source)
    report.dependency_counts[source] = len(names)


def parse_composer(report, path):
    data = load_json(path)
    if not isinstance(data, dict):
        return
    source = rel(report.root, path)
    deps = {}
    for key in ("require", "require-dev"):
        if isinstance(data.get(key), dict):
            deps.update(data[key])
    report.dependency_counts[source] = len(deps)
    for name in deps:
        report.add_dep(name, source)
    if "php" in deps:
        report.notes.append("PHP requirement %s (%s)" % (deps["php"], source))
    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    for name in scripts:
        if name in ("test", "lint", "analyse", "analyze", "stan"):
            kind = "test" if name == "test" else "lint"
            report.add_command(kind, "composer %s" % name, source)


def parse_go_mod(report, path):
    source = rel(report.root, path)
    text = read_text(path)
    names = re.findall(r"^\s*(?:require\s+)?([a-z0-9.\-]+\.[a-z]+/[^\s]+)\s+v[0-9]", text, re.M)
    report.dependency_counts[source] = len(names)
    for name in names:
        report.add_dep(name, source)
    m = re.search(r"^go\s+([0-9.]+)", text, re.M)
    if m:
        report.notes.append("Go version %s (%s)" % (m.group(1), source))
    report.add_command("test", "go test ./...", source)
    report.add_command("lint", "go vet ./...", source)
    report.add_command("build", "go build ./...", source)
    report.add_command("benchmark", "go test -bench . -benchmem ./...", source)


def parse_cargo(report, path):
    source = rel(report.root, path)
    text = read_text(path)
    names = set()
    section = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            section = s.strip("[]")
            continue
        if section and section.endswith("dependencies"):
            m = re.match(r"([A-Za-z0-9_\-]+)\s*=", s)
            if m:
                names.add(m.group(1))
    report.dependency_counts[source] = len(names)
    for name in names:
        report.add_dep(name, source)
    report.add_command("test", "cargo test", source)
    report.add_command("lint", "cargo clippy", source)
    report.add_command("build", "cargo build --release", source)
    if "[[bench]]" in text or "criterion" in names:
        report.add_command("benchmark", "cargo bench", source)


def parse_gemfile(report, path):
    source = rel(report.root, path)
    names = re.findall(r"""^\s*gem\s+['"]([^'"]+)['"]""", read_text(path), re.M)
    report.dependency_counts[source] = len(names)
    for name in names:
        report.add_dep(name, source)
        if name == "pg":
            report.add("database", "PostgreSQL", source)
        if name == "mysql2":
            report.add("database", "MySQL", source)


def parse_csproj(report, path):
    source = rel(report.root, path)
    text = read_text(path)
    names = re.findall(r'<PackageReference\s+Include="([^"]+)"', text)
    report.dependency_counts[source] = len(names)
    for name in names:
        report.add_dep(name, source)
    if 'Sdk="Microsoft.NET.Sdk.Web"' in text:
        report.add("framework", "ASP.NET Core", source)
    m = re.search(r"<TargetFrameworks?>([^<]+)<", text)
    if m:
        report.notes.append(".NET target %s (%s)" % (m.group(1), source))
    report.add_command("build", "dotnet build -c Release", source)
    report.add_command("test", "dotnet test", source)


def parse_jvm(report, path):
    source = rel(report.root, path)
    text = read_text(path)
    for token, label, category in (
        ("spring-boot", "Spring Boot", "framework"), ("quarkus", "Quarkus", "framework"),
        ("micronaut", "Micronaut", "framework"), ("ktor", "Ktor", "framework"),
        ("hibernate", "Hibernate", "database"), ("spring-boot-starter-data-jpa", "Spring Data JPA", "database"),
        ("postgresql", "PostgreSQL", "database"), ("mysql-connector", "MySQL", "database"),
        ("mongodb", "MongoDB", "database"), ("jedis", "Redis", "database"), ("lettuce", "Redis", "database"),
        ("junit", "JUnit", "test"), ("jmh", "JMH", "test"), ("com.android", "Android", "framework"),
    ):
        if token in text:
            report.add(category, label, source)
    base = os.path.dirname(path)
    if path.endswith("pom.xml"):
        mvn = "./mvnw" if os.path.exists(os.path.join(base, "mvnw")) else "mvn"
        report.add_command("test", "%s test" % mvn, source)
        report.add_command("build", "%s package -DskipTests" % mvn, source)
    else:
        gradle = "./gradlew" if os.path.exists(os.path.join(base, "gradlew")) else "gradle"
        report.add_command("test", "%s test" % gradle, source)
        report.add_command("build", "%s build -x test" % gradle, source)


def parse_makefile(report, path):
    source = rel(report.root, path)
    targets = re.findall(r"^([A-Za-z0-9_\-]+):", read_text(path), re.M)
    for target in targets:
        for kind in ("test", "lint", "build", "bench", "benchmark", "typecheck"):
            if target == kind:
                report.add_command("benchmark" if kind.startswith("bench") else kind, "make %s" % target, source)


def parse_compose(report, path):
    source = rel(report.root, path)
    for image in re.findall(r"^\s*image:\s*['\"]?([^\s'\"]+)", read_text(path), re.M):
        base = image.split("/")[-1].split(":")[0].lower()
        for key, label in COMPOSE_IMAGES.items():
            if base.startswith(key):
                report.add("database" if label not in ("RabbitMQ", "Kafka", "NATS", "MinIO") else "service",
                           label, source)


def parse_prisma(report, path):
    source = rel(report.root, path)
    m = re.search(r'provider\s*=\s*"(postgresql|mysql|sqlite|sqlserver|mongodb|cockroachdb)"', read_text(path))
    if m:
        report.add("database", m.group(1), source)


def parse_django_settings(report, path):
    source = rel(report.root, path)
    text = read_text(path)
    for token, label in (("postgresql", "PostgreSQL"), ("mysql", "MySQL"), ("sqlite3", "SQLite"),
                         ("oracle", "Oracle"), ("django_redis", "Redis cache")):
        if "django.db.backends.%s" % token in text or token in text and token == "django_redis":
            report.add("database", label, source)


def parse_env_example(report, path):
    source = rel(report.root, path)
    for line in read_text(path).splitlines():
        m = re.match(r"\s*(DATABASE_URL|DB_CONNECTION|REDIS_URL|MONGO(?:DB)?_URI)\s*=\s*([^\s#]*)", line)
        if not m:
            continue
        value = m.group(2).lower()
        for key, label in (("postgres", "PostgreSQL"), ("mysql", "MySQL"), ("sqlite", "SQLite"),
                           ("mongodb", "MongoDB"), ("redis", "Redis"), ("sqlsrv", "SQL Server")):
            if key in value or key in m.group(1).lower():
                report.add("database", label, source)


def git_state(root):
    try:
        inside = subprocess.run(["git", "-C", root, "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True, timeout=10)
        if inside.returncode != 0:
            return {"repository": False}
        branch = subprocess.run(["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, timeout=10).stdout.strip()
        head = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
        status = subprocess.run(["git", "-C", root, "status", "--porcelain"],
                                capture_output=True, text=True, timeout=30).stdout
        changed = [line for line in status.splitlines() if line.strip()]
        return {"repository": True, "branch": branch, "head": head,
                "clean": not changed, "uncommitted_changes": len(changed)}
    except (OSError, subprocess.SubprocessError):
        return {"repository": "unknown (git not available)"}


def scan(root):
    report = Report(root)
    lockfiles_by_dir = defaultdict(set)
    manifest_paths = []
    file_count = 0

    for dirpath, dirnames, filenames in os.walk(root):
        relative_dir = rel(root, dirpath)
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in IGNORED_DIRS and not d.startswith(".") or d in (".github", ".gitlab")
        )
        dirnames[:] = [d for d in dirnames if rel(root, os.path.join(dirpath, d)) not in IGNORED_DIRS]
        for name in filenames:
            file_count += 1
            path = os.path.join(dirpath, name)
            if name in LOCKFILES:
                lockfiles_by_dir[dirpath].add(LOCKFILES[name])
                report.package_managers.add("%s (%s)" % (LOCKFILES[name], rel(root, path)))
            if name in BUILD_FILES or name.endswith((".csproj", ".fsproj", ".sln")):
                report.build_systems.add("%s (%s)" % (BUILD_FILES.get(name, name.rsplit(".", 1)[-1]), rel(root, path)))
                manifest_paths.append(path)
            elif name.startswith("requirements") and name.endswith(".txt"):
                manifest_paths.append(path)
            elif name in ("schema.prisma", "settings.py", ".env.example", ".env.sample", ".env.dist"):
                manifest_paths.append(path)
            if relative_dir.startswith(".github/workflows") or name == ".gitlab-ci.yml" or name == "Jenkinsfile":
                report.ci.append(rel(root, path))
            if name in ENTRY_POINT_NAMES:
                report.entry_points.append(rel(root, path))
            lang = language_of(name)
            if lang:
                report.languages[lang] += 1
                try:
                    size = os.path.getsize(path)
                except OSError:
                    size = 0
                if size <= 5_000_000:
                    lines = count_lines(path)
                    report.language_lines[lang] += lines
                    if lang not in NON_SOURCE:
                        report.source_files.append((lines, rel(root, path)))

    for path in manifest_paths:
        name = os.path.basename(path)
        report.manifests.append(rel(root, path))
        lock_pm = next(iter(lockfiles_by_dir.get(os.path.dirname(path), {"npm"})), "npm")
        if name == "package.json":
            parse_package_json(report, path, lock_pm)
        elif name.startswith("requirements") and name.endswith(".txt"):
            parse_requirements(report, path)
        elif name == "pyproject.toml":
            parse_pyproject(report, path)
        elif name == "composer.json":
            parse_composer(report, path)
        elif name == "go.mod":
            parse_go_mod(report, path)
        elif name == "Cargo.toml":
            parse_cargo(report, path)
        elif name == "Gemfile":
            parse_gemfile(report, path)
        elif name.endswith((".csproj", ".fsproj")):
            parse_csproj(report, path)
        elif name in ("pom.xml", "build.gradle", "build.gradle.kts"):
            parse_jvm(report, path)
        elif name == "Makefile":
            parse_makefile(report, path)
        elif name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
            parse_compose(report, path)
        elif name == "schema.prisma":
            parse_prisma(report, path)
        elif name == "settings.py":
            parse_django_settings(report, path)
        elif name.startswith(".env."):
            parse_env_example(report, path)
        elif name == "artisan":
            report.add_command("test", "php artisan test", rel(root, path))

    if report.languages.get("Python") and not any(c["kind"] == "test" for c in report.commands):
        if any("pytest" in label for label in report.detected.get("test", ())):
            report.add_command("test", "pytest", "detected pytest dependency")
    report.git = git_state(root)
    report.file_count = file_count
    return report


def tool_installed(root, command):
    """Whether the first word of a candidate command resolves to an executable."""
    tool = command.split()[0]
    if tool.startswith("./"):
        return "yes" if os.path.exists(os.path.join(root, tool[2:])) else "no"
    return "yes" if shutil.which(tool) else "no"


def to_dict(report, top):
    total_lines = sum(report.language_lines.values()) or 1
    languages = [
        {"language": lang, "files": report.languages[lang], "lines": report.language_lines[lang],
         "share": round(100.0 * report.language_lines[lang] / total_lines, 1)}
        for lang, _ in sorted(report.language_lines.items(), key=lambda kv: -kv[1])
    ]
    return {
        "root": report.root,
        "files_scanned": report.file_count,
        "git": report.git,
        "languages": languages,
        "frameworks": sorted(report.detected.get("framework", ())),
        "libraries": sorted(report.detected.get("library", ())),
        "build_tools": sorted(report.detected.get("build", ())),
        "build_systems": sorted(report.build_systems),
        "package_managers": sorted(report.package_managers),
        "databases": sorted(report.detected.get("database", ())),
        "external_services": sorted(report.detected.get("service", ())),
        "test_tools": sorted(report.detected.get("test", ())),
        "lint_tools": sorted(report.detected.get("lint", ())),
        "dependency_counts": report.dependency_counts,
        "entry_points": sorted(set(report.entry_points))[:50],
        "commands": [dict(c, tool_installed=tool_installed(report.root, c["command"])) for c in report.commands],
        "ci": sorted(report.ci),
        "notes": report.notes,
        "largest_source_files": [
            {"path": p, "lines": n} for n, p in sorted(report.source_files, reverse=True)[:top]
        ],
    }


def print_markdown(data):
    out = []
    out.append("# OptimizeIT Discovery: %s" % data["root"])
    out.append("")
    out.append("Files scanned: %d" % data["files_scanned"])
    git = data["git"]
    if git.get("repository") is True:
        out.append("Git: branch `%s` at `%s`, %s" % (
            git["branch"], git["head"],
            "clean working tree" if git["clean"] else "%d uncommitted change(s) - do not overwrite them" % git["uncommitted_changes"]))
    else:
        out.append("Git: %s" % ("not a repository" if git.get("repository") is False else git.get("repository")))
    out.append("")

    out.append("## Languages")
    if data["languages"]:
        out.append("| Language | Files | Lines | Share |")
        out.append("|---|---:|---:|---:|")
        for row in data["languages"]:
            out.append("| %s | %d | %d | %.1f%% |" % (row["language"], row["files"], row["lines"], row["share"]))
    else:
        out.append("_none detected_")
    out.append("")

    sections = [
        ("Frameworks (declared)", "frameworks"), ("Libraries of interest (declared)", "libraries"),
        ("Build tools", "build_tools"), ("Build systems / manifests", "build_systems"),
        ("Package managers (lockfiles)", "package_managers"), ("Databases and data stores (declared)", "databases"),
        ("External services (declared)", "external_services"), ("Test tools", "test_tools"),
        ("Lint / type-check tools", "lint_tools"), ("Entry point candidates", "entry_points"),
        ("CI configuration", "ci"), ("Version notes", "notes"),
    ]
    for title, key in sections:
        out.append("## %s" % title)
        items = data[key]
        if items:
            out.extend("- %s" % item for item in items)
        else:
            out.append("_none detected_")
        out.append("")

    out.append("## Dependency counts")
    if data["dependency_counts"]:
        out.extend("- %s: %d" % (k, v) for k, v in sorted(data["dependency_counts"].items()))
    else:
        out.append("_none detected_")
    out.append("")

    out.append("## Candidate commands (verify before running)")
    if data["commands"]:
        out.append("| Kind | Command | Tool installed? | Source |")
        out.append("|---|---|---|---|")
        for c in data["commands"]:
            out.append("| %s | `%s` | %s | %s |" % (c["kind"], c["command"], c["tool_installed"], c["source"]))
    else:
        out.append("_none detected_")
    out.append("")

    out.append("## Largest source files")
    if data["largest_source_files"]:
        out.extend("- %s (%d lines)" % (f["path"], f["lines"]) for f in data["largest_source_files"])
    else:
        out.append("_none detected_")
    out.append("")
    out.append("> Heuristic output. \"Declared\" means listed in a manifest, not necessarily imported or used.")
    out.append("> Entry points are incomplete. Verify by reading the manifests and code before drawing conclusions.")
    print("\n".join(out))


def main(argv=None):
    parser = argparse.ArgumentParser(description="OptimizeIT project discovery")
    parser.add_argument("path", nargs="?", default=".", help="project directory (default: current directory)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    parser.add_argument("--top", type=int, default=10, help="number of largest source files to list")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print("Not a directory: %s" % root, file=sys.stderr)
        return 2
    data = to_dict(scan(root), args.top)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_markdown(data)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.exit(main())
