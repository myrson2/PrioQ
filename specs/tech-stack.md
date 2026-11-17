# Tech Stack — Smart Student Task Prioritization Queue System

## Core Stack Matrix
| Layer | Technology | Version | Rationale |
|---|---|---|---|
| Language / env | Python, managed by **uv** | 3.12 | uv installed; Python not on PATH, so uv provisions it; lockfile reproducibility |
| API | FastAPI (+ Pydantic v2) | latest stable | auto `/docs`, typed validation |
| ORM | SQLAlchemy, **sync** style | 2.0 | simpler to learn/debug; sufficient for single-student load |
| Database | **MySQL** (InnoDB, utf8mb4) | 8.0 (local `MySQL80` service) | owner preference; hosted-friendly |
| Driver | PyMySQL + `cryptography` | latest | pure Python (easy on Windows); `cryptography` needed for MySQL 8's default auth |
| Migrations | Alembic | latest | schema will change in M3 |
| Auth | PyJWT (HS256), pwdlib[argon2], OAuth2 password flow | latest | works with Swagger "Authorize" |
| Config | pydantic-settings + `.env` | latest | typed settings, secrets out of git |
| Testing | pytest + httpx (TestClient) against `taskqueue_test` MySQL DB | latest | catches MySQL-specific behavior |
| Frontend (M2) | React, Vite, TypeScript, Tailwind CSS, fetch/Axios | — | per `project.txt` |
| ML (M3) | Pandas, scikit-learn `RandomForestRegressor` | — | per `project.txt`; dataset from open source |
| Hosting (M2+) | Vercel (frontend), Render web service (backend), managed MySQL provider (chosen at deploy time) | — | Render has no managed MySQL |

## Layer Boundaries
```
Router (FastAPI)     → HTTP only: parse/validate, call service, map errors to status codes
Service              → business rules, ownership-scoped queries, calls scoring
Scoring (pure)       → compute_priority / sort_tasks; no DB, no FastAPI; `now` injected
Persistence          → SQLAlchemy models + Session; Alembic owns the schema
```
Code is organised by feature (`auth/`, `users/`, `tasks/`) with shared `core/` (config, database, security).

## Database Conventions
- Connection URL: `mysql+pymysql://<user>:<pass>@localhost:3306/taskqueue?charset=utf8mb4`; tests use `TEST_DATABASE_URL` → `taskqueue_test`.
- `pool_pre_ping=True` (hosted MySQL drops idle connections).
- Every `String` has an explicit length (MySQL `VARCHAR` requires it).
- Enums stored as `VARCHAR` with a check constraint (`native_enum=False`) so adding a category in a later migration is a simple change.
- A `UTCDateTime` type decorator, because MySQL `DATETIME` stores no timezone.

## Rejected Alternatives & Forbidden Patterns
| Rejected | Why |
|---|---|
| SQLite | replaced by owner's choice of MySQL (see constitution amendment) |
| SQLite for tests | hides MySQL behavior differences |
| Async SQLAlchemy | unnecessary complexity at this scale (not forbidden; needs amendment) |
| Session cookies | JWT bearer chosen for a separate Vercel frontend + Swagger testing |
| Refresh tokens | 7-day access token is enough for personal use / short testing windows |
| Backend on Vercel serverless | poor fit for a stateful FastAPI + DB-pool app |
| Poetry / pip+venv | uv already installed and handles Python itself |

**Forbidden patterns:** reading auth headers outside `get_current_user`; fetching another user's row then checking ownership in Python; raw SQL string formatting; storing computed scores; committing `.env` or credentials; `create_all` against a non-test database.
