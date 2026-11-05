# Running StayNest locally

StayNest runs as three services with one command:

```bash
./scripts/start_local.sh
```

That command starts PostgreSQL, FastAPI, and the React/Vite app, applies the
schema, seeds an empty database with deterministic development data, waits for
every service to become healthy, and prints the URLs. Re-running it is safe:
already-running services are reused and **no database data is ever deleted**.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| Node.js + npm | 18+ | `node --version`, `npm --version` |
| PostgreSQL tools | 14+ | `initdb`, `pg_ctl`, `psql`, `pg_isready`, `createdb` |

Install PostgreSQL if it is missing:

```bash
# macOS (Homebrew)
brew install postgresql@16
brew link --force postgresql@16

# macOS (Postgres.app) — add this to PATH instead
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-client
```

The script also finds Homebrew's `postgresql@15`/`postgresql@18` and
Postgres.app installations even when they are not on `PATH`. Docker is optional
(see [Docker Compose](#docker-compose-alternative)).

## One-command startup

```bash
git clone https://github.com/vsh2504/team3-vacation-rentals.git
cd team3-vacation-rentals
./scripts/start_local.sh
```

First run takes a few minutes because it creates `.venv`, installs Python and
npm dependencies, and initializes the database cluster. Later runs start in
seconds because dependencies and data are reused.

### What the script does

1. **Validates prerequisites** — Python/Node versions, missing tools, and port
   conflicts are reported before anything is started.
2. **Installs only what changed** — `.venv` is reused; `pip install` and
   `npm ci` run only when `requirements.txt` or the npm lockfile changes.
3. **Starts project-local PostgreSQL** — data lives in `.local/postgres-data`
   on `127.0.0.1:55432` by default, so it cannot clash with a system Postgres on
   5432. The cluster uses loopback trust authentication for development only.
4. **Applies migrations** — `backend/db/migrations/001_init.sql` is idempotent
   (`CREATE ... IF NOT EXISTS`); existing rows and tables are left untouched.
5. **Seeds deterministically** — only when the database is empty: 5 users and
   24 listings (20 approved, 4 pending). Seeded IDs are stable.
6. **Starts FastAPI** on `http://127.0.0.1:8000` with
   `STAYNEST_DB_URL` pointing at PostgreSQL.
7. **Starts Vite** on `http://127.0.0.1:5173` with `/api` proxied to the API.
8. **Waits for readiness** and verifies the API, the web server, and the proxy
   before printing the summary.

### URLs and demo logins

| Service | URL |
|---|---|
| Web app | <http://127.0.0.1:5173> |
| API | <http://127.0.0.1:8000> |
| API health | <http://127.0.0.1:8000/health> |
| Swagger UI | <http://127.0.0.1:8000/docs> |
| PostgreSQL | `postgresql://staynest@127.0.0.1:55432/staynest` |

Demo accounts (development seed only):

| Role | Email | Password |
|---|---|---|
| Admin | `admin@staynest.local` | `admin12345` |
| Host | `host1@staynest.local` … `host4@staynest.local` | `password123` |
| Customer | `customer@staynest.local` | `password123` |

Register new customers and hosts from `/auth`; their rows persist in PostgreSQL.

## Day-to-day commands

```bash
./scripts/start_local.sh              # start or repair everything
./scripts/health_local.sh             # check DB, API, search, web, and proxy
./scripts/logs_local.sh               # last 200 lines of each log
./scripts/logs_local.sh api -f        # follow the FastAPI log
./scripts/logs_local.sh web -n 50     # last 50 Vite lines
./scripts/logs_local.sh db            # PostgreSQL + initdb logs
./scripts/stop_local.sh               # stop all three, keep all data
./scripts/stop_local.sh --keep-db     # stop app, leave PostgreSQL running
./scripts/check_local.sh              # backwards-compatible alias for health
```

Logs and PID files live in `.local/logs/` and `.local/run/` (gitignored).
`health_local.sh` exits non-zero and prints the exact start/log command for each
failed check.

## Data persistence

`./scripts/stop_local.sh` stops the processes but leaves the PostgreSQL data
directory in place. The next `./scripts/start_local.sh` reads the existing rows —
users, listings (including contact/hours/photos/videos and moderation state),
bookings, reviews, and analytics inputs all survive restarts.

To verify manually:

```bash
./scripts/start_local.sh
# create a listing/booking in the UI, then:
./scripts/stop_local.sh
./scripts/start_local.sh
./scripts/health_local.sh   # row counts should match the previous run
```

Use `./scripts/logs_local.sh db` if PostgreSQL refuses to start; never delete
`.local/postgres-data` unless you intentionally want a fresh environment.

<details>
<summary>Start over from an empty local database (destroys local data)</summary>

```bash
./scripts/stop_local.sh
rm -rf .local/postgres-data
./scripts/start_local.sh
```

For Docker Compose, `docker compose down -v` deletes the `pgdata` volume. Both
commands are destructive; the normal stop/start workflow never does this.
</details>

## Configuration

Native scripts read optional overrides from `.env.local` (gitignored). Start
from the checked-in example:

```bash
cp .env.local.example .env.local
```

| Variable | Default | Purpose |
|---|---|---|
| `STAYNEST_PGPORT` | `55432` | Host port for the project-local PostgreSQL |
| `STAYNEST_PGHOST` | `127.0.0.1` | PostgreSQL listen address (keep on loopback) |
| `STAYNEST_PGUSER` | `staynest` | Cluster superuser and database user |
| `STAYNEST_PGDATABASE` | `staynest` | Database name |
| `STAYNEST_PGDATA` | `.local/postgres-data` | Data directory (never deleted by scripts) |
| `STAYNEST_API_PORT` | `8000` | FastAPI port |
| `STAYNEST_WEB_PORT` | `5173` | Vite port |
| `STAYNEST_RELOAD` | `0` | `1` runs `uvicorn --reload` for backend hot reload |
| `JWT_SECRET` | dev value | Token signing secret; replace outside development |
| `STAYNEST_DB_URL` | bundled cluster | Use an existing database; disables local cluster management |

`STAYNEST_DB_URL` is the canonical backend variable (the API does **not** read
`DATABASE_URL`). Examples:

```bash
# Existing PostgreSQL
STAYNEST_DB_URL=postgresql+psycopg://user:password@127.0.0.1:5432/staynest ./scripts/start_local.sh

# SQLite (schema and deterministic seed still run; migrations file is skipped)
STAYNEST_DB_URL=sqlite:///./staynest.db ./scripts/start_local.sh
```

When an external database is configured, `start_local.sh` skips cluster
management and `stop_local.sh` never stops that database.

## Docker Compose alternative

The Compose stack follows the same contract as the native script: PostgreSQL
health → API health → web health, persistent `pgdata` volume, and the Vite
proxy targeting the API container.

```bash
cp .env.example .env
docker compose up --build -d        # build + start in the background
docker compose ps                   # wait for all three to be "healthy"
docker compose logs -f api          # follow API logs
docker compose down                 # stop; pgdata volume is preserved
```

URLs are the same (`localhost:5173`, `localhost:8000`). `STAYNEST_PGPORT`,
`STAYNEST_API_PORT`, and `STAYNEST_WEB_PORT` in `.env` change only the host
ports. `docker compose down -v` is the destructive reset.

Compose details worth knowing:

- `backend/db/migrations/001_init.sql` is mounted into
  `/docker-entrypoint-initdb.d/`, so a brand-new volume gets the schema before
  the API starts. Existing volumes are never re-initialized.
- The API container receives `STAYNEST_DB_URL=postgresql+psycopg://…@db:5432/…`
  and the web container receives `STAYNEST_API_URL=http://api:8000`, which
  `frontend/vite.config.js` uses as the proxy target.
- API and web health checks use `python`/`node` already present in their images,
  so no extra `curl` package is needed.

## Manual startup (three terminals)

Useful when debugging one component; the one-command script is the supported
path.

```bash
# Terminal 1 — PostgreSQL (after ./scripts/start_local.sh once)
export STAYNEST_DB_URL=postgresql+psycopg://staynest@127.0.0.1:55432/staynest

# Terminal 2 — API
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 3 — web
cd frontend
npm install
STAYNEST_API_URL=http://127.0.0.1:8000 npm run dev
```

The API creates missing tables and seeds an empty database on startup. Apply the
SQL baseline manually only if you prefer to provision the database separately:

```bash
psql postgresql://staynest@127.0.0.1:55432/staynest \
  -v ON_ERROR_STOP=1 -f backend/db/migrations/001_init.sql
```

Migrations use psql's libpq URL format; strip SQLAlchemy's driver suffix from
`STAYNEST_DB_URL` (`postgresql+psycopg://` → `postgresql://`).

## Demo flow

See `docs/demo-script.md` for the four-minute rehearsal. Short version:

1. Search by dates, guests, city/state/ZIP or address; open a listing to see
   photos, amenities, cost, rating, reviews, `# booked today`, and the map.
2. Log in as a customer, book, try the same dates again (409), then cancel.
3. Log in as a host, create a listing (stays `PENDING_APPROVAL`), log in as admin
   and approve it — it appears in search.
4. Review a completed past booking; open Host and Admin analytics for 30/60/90
   days and ZIP filters.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Missing required tools: postgresql` | Install PostgreSQL tools (see [Prerequisites](#prerequisites)) or set `STAYNEST_DB_URL`. |
| `Port 55432 is already in use` | Another Postgres owns the port. Set `STAYNEST_PGPORT=55433` in `.env.local`, or stop the other server. |
| `Port 8000/5173 is already in use` | Stop the process shown in the error, or set `STAYNEST_API_PORT` / `STAYNEST_WEB_PORT`. |
| `Project PostgreSQL is already running on port …` | The cluster is running with a different `STAYNEST_PGPORT`. Run `./scripts/stop_local.sh`, then start with the original port. |
| API health fails right after start | `./scripts/logs_local.sh api`; the trap also prints the last 20 lines. Common causes: dependency install interrupted, `backend/app` import error, or a port race. |
| `Cannot connect to STAYNEST_DB_URL` | Check the external URL, credentials, and that the server is reachable. The native script does not manage external databases. |
| Web loads but API calls 404 | Vite config changed without a restart, or `STAYNEST_API_URL` points elsewhere. `./scripts/stop_local.sh && ./scripts/start_local.sh`. |
| Web loads but shows seed fallback data | Run `./scripts/health_local.sh`; verify `/api/health` through the Vite proxy and check `.local/logs/api.log`. |
| `initdb: directory exists but is not empty` | `STAYNEST_PGDATA` points at a non-cluster directory. Move it or choose a new path. |
| PostgreSQL version mismatch in `.local/` | The data directory was created by another major version. Point `STAYNEST_PGDATA` at a new directory (old data is preserved) or run the matching `pg_ctl`. |
| Old schema missing new columns | The project-local cluster is created fresh by this workflow. For an older database, back it up and recreate it with `001_init.sql`; do not delete data blindly. |
| `permission denied: ./scripts/...` | `chmod +x scripts/*.sh`. |
| Docker build copies host `node_modules` / fails on Vite | `.dockerignore` now excludes `node_modules`, `dist`, and env files; rebuild with `docker compose build --no-cache web`. |

## Verification / requirement traceability

This workflow implements Requirement 7:

- **7.1** `start_local.sh` validates prerequisites and brings up PostgreSQL,
  FastAPI, and React with one command and compatible configuration.
- **7.2** Data lives in a persistent PostgreSQL directory/volume; stop and start
  do not delete rows, so users, listings, bookings, reviews, moderation state,
  and extended listing fields survive restarts.
- **7.3** The API applies schema creation/migrations and deterministic seeding
  only when the database is empty; the SQL baseline is idempotent.
- **7.4** `start_local.sh` waits for readiness, and `health_local.sh` reports
  per-service status, row counts, URLs, and actionable failure hints.
