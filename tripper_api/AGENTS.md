# FastAPI backend conventions

## Scope and intent

These instructions apply to the `tripper_api/` subtree. Follow them when making backend changes and updating the tests and configuration needed by those changes.

Preserve unrelated worktree changes. Prefer correctness and architectural consistency, with production safety as a constraint. Avoid unrelated refactors.

## Feature structure and responsibilities

- Organize by feature and prefix filenames with the feature/package name using Python snake_case: for example, `owner/owner_controller.py`, `owner/owner_service.py`, `owner/owner_dto.py`, `owner/owner_repository.py`, and `owner/owner_model.py` as needed. Extract useful modules rather than creating empty layers.
- Place shared database, configuration, security, and error infrastructure in `core/`.
- Controllers handle HTTP input, dependencies, status codes, and response mapping. Keep business rules and SQL out of controllers.
- Services implement business operations and resource-level authorization. Keep FastAPI `Depends` and HTTP exceptions out of services and repositories.
- Repositories encapsulate SQLAlchemy queries and persistence operations. Prefer meaningful feature-specific operations over generic CRUD frameworks.
- Use concrete service and repository classes with explicit constructor dependencies. Do not require interfaces, abstract base classes, or a unit-of-work abstraction. Pure helpers may be ordinary functions.
- Use FastAPI dependency functions to assemble services and repositories. Keep dependencies explicit; avoid service locators and hidden mutable global state.
- Retain an injectable app factory so tests can supply their own configuration and dependencies.

## Async execution and persistence

- PostgreSQL is the only database for development, integration tests, and production. Do not introduce SQLite fallbacks.
- Use stable SQLAlchemy 2.x ORM with Psycopg 3, an async engine, and an explicit `postgresql+psycopg_async://` connection URL.
- Use separate SQLAlchemy persistence models and Pydantic v2 DTOs. Do not introduce SQLModel without an explicit architecture decision.
- Request handlers and I/O operations must use async-compatible APIs. Do not perform blocking database, network, or filesystem work on the event loop. Pure computation and dependency factories need not be `async def`.
- A process-wide engine and session factory are appropriate. Scope each `AsyncSession` to a request or independent background operation; never share one session across concurrent tasks.
- Manage app-owned engines and external clients through FastAPI lifespan. Initialize them per application instance, close clients and await engine disposal on shutdown, and avoid import-time resource initialization.
- Services own explicit transaction boundaries. Repositories participating in an operation use the same session and may flush, but must never independently commit.
- Ensure dependency/authentication queries do not accidentally open a transaction on the same session before a service starts its transaction. Make session and transaction lifetimes deliberate.
- Use database constraints and appropriate concurrency control for invariants; a transaction alone does not prevent all races.
- Avoid implicit lazy-loading I/O with async ORM use. Load the data needed by the operation and response explicitly.
- Normally configure async sessions with `expire_on_commit=False` and explicitly load any required database-generated values. DTO mapping and response serialization must not trigger implicit database reads after commit or session closure.

## Schema evolution

- Use Alembic for every storage schema change. Commit migrations alongside the corresponding model changes.
- Review generated migrations, including effects on existing data, constraints, indexes, and required backfills.
- Apply migrations explicitly during setup or deployment. Application startup must not modify schemas or call `create_all()`.
- Document migration data impact and rollback strategy. Mark irreversible changes explicitly rather than providing misleading downgrades.
- Require explicit authorization for destructive migrations.

## API, authorization, and errors

- Treat existing routes, status codes, and snake_case JSON fields as stable contracts. Breaking changes require explicit approval and coordinated client/test updates.
- Define explicit Pydantic request and response DTOs. Reject unknown write fields and derive identity, ownership, and roles from trusted server state.
- Authenticate through FastAPI dependencies; enforce resource-level authorization in the service performing the operation. Management endpoints require authentication; public endpoints must be intentionally public.
- Authentication overrides belong in tests, never production bypasses.
- Services raise application-specific exceptions. Central FastAPI handlers map them to HTTP status codes and a consistent response shape: `{"error": {"code": "stable_code", "message": "Public message"}}`.
- Handle validation errors consistently. Log unexpected errors server-side and return a generic 500 response without internal details or secrets.
- Follow the task's supplied specification for product behavior. `../CONTEXT.md` defines shared domain terminology.

## Configuration and dependencies

- Use one typed `pydantic-settings` configuration model, populated from environment variables and validated at startup.
- Allow an ignored local `.env`; commit an `.env.example` containing placeholders only. Never commit secrets.
- Pass settings explicitly to components that need them; avoid scattered environment reads. Tests supply isolated settings.
- Manage Python dependencies through `uv`. Commit `pyproject.toml` and `uv.lock` together, and use `uv sync --locked` in CI with the configured test/development dependency groups or extras.
- Retain the existing build backend unless a task justifies changing it.
- The stack selected here is approved. Explain ordinary supporting dependency additions; discuss new major frameworks or external services before introducing them.

## Tests and quality checks

- Use pytest. Test pure business rules without a database where appropriate.
- Run persistence and API integration tests against isolated PostgreSQL initialized through Alembic migrations. Do not substitute SQLite or repository mocks for database integration coverage.
- Exercise application lifespan in integration tests so resource initialization and cleanup run. When using an async HTTP test client, manage lifespan explicitly.
- Use Docker Compose for local test PostgreSQL and a PostgreSQL service container in GitHub Actions. Do not introduce Testcontainers at this stage.
- Use an explicit test database URL and guarded cleanup targeting only the isolated test database. Keep tests independent. Align the PostgreSQL major version across local tests, CI, and production.
- Exercise concurrency-sensitive operations using separate sessions. Test relevant authorization, validation, rollback, persistence, and public/private response boundaries.
- Substitute external Google and email integrations in ordinary tests; do not require real accounts or send real email.
- Use Ruff for formatting and linting, and strict mypy for the backend package. Annotate service/repository methods, DTOs, and dependency functions. Keep configuration in `pyproject.toml`; explain narrowly scoped suppressions.
- Declare Ruff and mypy as project development dependencies; editor extensions alone are insufficient.
- Run focused checks during development and the full configured backend checks before completion. Run cross-stack end-to-end checks when API contracts or integrated behavior change.

Run checks from the repository root:

```text
uv run ruff format --check .
uv run ruff check .
uv run mypy tripper_api
uv run pytest
```

Report checks that are unavailable or prohibitively slow and what was actually run. Do not claim success for checks that were skipped.
