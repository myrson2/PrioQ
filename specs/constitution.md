# Constitution — Smart Student Task Prioritization Queue System

**Status:** Ratified 2026-11-17 · **Applies to:** all milestones · **Amendments:** only by explicit owner decision, recorded in the Amendment Log at the bottom.

## 1. Core Axioms
1. **Explainable priority.** Every priority score the API returns comes with its breakdown (the factors and their values). No ranking may be returned that the student can't trace back to inputs. This holds for the M3 ML model too: it must return at least the features it used and the baseline formula score alongside its prediction.
2. **Privacy by default.** A student can never see, change, or infer the existence of another student's data. Cross-user access to any resource returns `404 Not Found`, identical to a resource that doesn't exist.
3. **Test-first.** Every feature ships with automated tests in the same change. Priority/scoring logic is pure (no DB, no web framework, time injected as a parameter) and is unit-tested with fixed reference values.

## 2. Security & Auth Invariants
- **S-1 Single gateway.** Every protected route depends on exactly one dependency, `get_current_user`. No route reads tokens or headers itself.
- **S-2 Ownership in the query.** Every query on user-owned data filters by `owner_id = current_user.id` *in the database query*, never by fetching then checking in Python.
- **S-3 404 masking.** Not-found and not-yours produce the same status and the same body.
- **S-4 Credentials.** Passwords hashed with Argon2; never logged, never returned. JWTs (HS256) signed with `SECRET_KEY` from the environment; the app refuses to start without it. No secrets in git (`.env` ignored, `.env.example` committed).
- **S-5 Least-privilege DB user.** The app connects with a dedicated MySQL user scoped to its own databases, never `root`.

## 3. Data Integrity & Database Standards
- **D-1 MySQL 8 / InnoDB / `utf8mb4`** for every environment, including tests (a separate `_test` database). No SQLite anywhere.
- **D-2 Migrations only.** All schema changes go through Alembic revisions; the app never calls `create_all` against a real database (tests may build their throwaway schema directly).
- **D-3 Cascading ownership.** Every user-owned table has `FOREIGN KEY ... ON DELETE CASCADE` to `users.id`, mirrored by an ORM cascade.
- **D-4 UTC everywhere.** Datetimes are stored as UTC and returned with a `Z`/offset; inputs without a timezone offset are rejected.
- **D-5 Derived values aren't stored.** Priority scores are computed at read time from stored inputs and an injected `now`; no score columns. (M3 may store model *artifacts*, not per-task scores.)
- **D-6 Validate at the edge.** All input bounds are enforced by Pydantic schemas; DB constraints (NOT NULL, FK, unique) back them up.

## 4. Milestone 1 Scope Discipline
| Strictly in scope | Strictly out of scope (forbidden in M1) |
|---|---|
| Accounts (register / login / me / delete) with JWT | Docker / containers |
| Task CRUD scoped to owner | Caching layers (Redis etc.) |
| Deadline + smart (rule-based) queue with breakdown | Any ML / Pandas / scikit-learn code |
| Alembic migrations on MySQL | Frontend code and CORS setup |
| pytest suite against a real MySQL test DB | Email sending (verification, password reset) |
| Manual verification via `/docs` | Deployment / hosting config |

Not forbidden but not chosen: async DB access / background workers. M1 uses sync SQLAlchemy; switching needs a tech-stack amendment.

## 5. Amendment Log
| Date | Change | Reason |
|---|---|---|
| 2026-11-17 | SQLite → MySQL 8 (supersedes `project.txt`) | Owner preference; matches hosted deployment plan |
