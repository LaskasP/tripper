# Tripper

Tripper is a public trip guide with a TypeScript/Vite frontend and an asynchronous
FastAPI/PostgreSQL backend in progress.

## Development

Install locked backend dependencies and frontend dependencies:

```powershell
python -m pip install uv
python -m uv sync --locked --extra test
npm --prefix tripper_ui install
```

Copy `.env.example` to `.env`, replace its placeholder password, create the named
PostgreSQL database, and apply migrations explicitly:

```powershell
python -m uv run alembic upgrade head
```

Run the API and frontend in separate terminals:

```powershell
python run.py
npm --prefix tripper_ui run dev
```

The checked-in Los Angeles JSON under `legacy_data/los_angeles` is import input only;
the application never reads or serves it at runtime. My Trips is available at
`/tripper/my-trips`; configure `TRIPPER_GOOGLE_CLIENT_ID` for its direct Google
sign-in. Tripper stores opaque, seven-day server-side Sessions and never stores Google
access or refresh tokens. PostgreSQL is the only runtime store; application startup
never creates or migrates schemas.

Import the Los Angeles guide for an existing Creator Account after applying migrations.
The dry-run performs the complete validation and conflict check without writing:

```powershell
python -m uv run python -m tripper_api.legacy_import --creator-id <account-uuid> --dry-run
python -m uv run python -m tripper_api.legacy_import --creator-id <account-uuid>
```

The command pins the reviewed source hash, imports all content in one transaction, and
records import history. An identical rerun is a no-op. The imported guide remains a
private Draft readable only by current Participants; publication is a separate cutover
operation.

Run the complete application with Docker Compose:

```powershell
docker compose up --build
```

Open the UI at `http://localhost:8080/tripper/`. The API is available directly
at `http://localhost:8000`, with Swagger docs at `http://localhost:8000/docs`.
The same docs are also proxied through the UI at `http://localhost:8080/docs`.

Stop the stack with `docker compose down`. Add `-v` to also remove the local
PostgreSQL volume.

## Verification

```powershell
docker compose -f compose.test.yml up -d --wait
python -m uv run ruff format --check .
python -m uv run ruff check .
python -m uv run mypy tripper_api
python -m uv run pytest
npm --prefix tripper_ui run test:e2e
```

The backend and end-to-end suites use the isolated `tripper_test` database on
PostgreSQL 17. The end-to-end runner starts and stops that Compose service itself,
applies Alembic migrations, injects a test identity, and drives the browser through
trip creation and public viewing.
