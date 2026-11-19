# Day 2 Execution Brief: Database Models & Migration Harness

**Feature Folder:** `specs/feature/2026-11-19-day2-models-migrations/`  
**Assignee:** Backend Engineer  
**Role:** Tech Lead / Senior Architect  
**Time Budget:** ~2.5 Hours (Strict hard cap: < 4.0 Hours)  
**Governing Documents:** [`specs/constitution.md`](specs/constitution.md), [`AGENTS.md`](AGENTS.md)

---

## Lead Architect's Note
Day 1 is accepted as complete; today we make the domain persistent. Deliver three owner-scoped tables, a single native-MySQL Alembic revision, and a test harness that physically cannot point at a production database. Follow TDD strictly: failing test first, observe the failure, implement, verify. No routers today, no changes to `app/tasks/scoring.py`, and no git commits.

---

## Task 3: Models, initial migration, and MySQL test harness (~2.5 hrs)

### Objective
Define `User`, `Course`, `Task`, and `TaskCategory`; generate and verify the initial Alembic migration; build the guarded `taskqueue_test` harness with schema verification tests.

### Architectural Invariants & Constraints
- Day 1 harness only: `Base`, `UTCDateTime`, `utcnow` from `app/core/database.py`, `get_settings` from `app/core/config.py` (D-4).
- MySQL 8 / InnoDB / `utf8mb4` in every environment; SQLite forbidden (D-1). `sa.Double`, never `sa.Float`.
- Migrations only — no `create_all` (D-2). No score columns (D-5). No naive timestamps (D-4).
- `users.id` cascades; `courses.id` sets null on `tasks` (D-3). Every string column has an explicit length (D-6).
- All commands via `uv run`; no commits.

### Files to Create
- `app/users/__init__.py`, `app/users/models.py`
- `app/courses/__init__.py`, `app/courses/models.py`
- `app/tasks/models.py`, `app/models.py`
- `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/<rev>_create_users_courses_tasks.py`
- `tests/conftest.py`, `tests/test_migrations.py`

### Specification & Interface Requirements
- Consumes: `Base`, `UTCDateTime`, `utcnow` (`app.core.database`), `get_settings` (`app.core.config`).
- Produces: `User` (VARCHAR 50/320 uniques, `Double` hours, UTC timestamps, ORM cascade with `passive_deletes=True`); `Course` (owner FK cascade, name/code/color); `Task` + `TaskCategory` (owner FK cascade, optional course FK set-null, enum stored `native_enum=False, create_constraint=True, length=20`); `app.models` aggregator; `tests/conftest.py` fixtures `test_engine`, `db_session`.
- Readiness check before any migration (MySQL setup unconfirmed):
  ```bash
  uv run python -c "from app.core.config import get_settings; from sqlalchemy import create_engine, text; from sqlalchemy.engine import make_url; s=get_settings(); u=make_url(s.test_database_url); assert u.database and u.database.endswith('_test'), u.database; print(create_engine(s.test_database_url).scalar(text('SELECT DATABASE()')))"
  ```
  Expected output: `taskqueue_test`. If it fails, complete the MySQL setup in `implementation.md` §1 first.

### Edge Cases You Must Cover in `tests/test_migrations.py`
- [ ] `test_upgrade_creates_expected_tables` — `users`, `courses`, `tasks`, `alembic_version` exist.
- [ ] `test_foreign_keys_use_cascade_and_set_null` — correct FK actions on both columns.
- [ ] `test_double_and_datetime_columns` — floats are `DOUBLE`, dates are `DATETIME(6)`.
- [ ] `test_test_database_name_is_guarded` — non-`_test` DB name aborts before destructive SQL.
- [ ] `test_upgrade_downgrade_cycle` — downgrade to base then re-upgrade succeeds.

### Step-by-Step Execution Plan
1. Run the readiness check above; stop if it fails.
2. Write the five failing tests in `tests/test_migrations.py`.
3. Run `uv run pytest tests/test_migrations.py -v`; confirm FAIL.
4. Implement the models and `app/models.py`; run `uv run alembic init alembic` and wire `env.py`.
5. Run `uv run alembic revision --autogenerate -m "create users courses and tasks"`, inspect native MySQL DDL, then `uv run alembic upgrade head`.
6. Implement `tests/conftest.py` (guard, session upgrade, autouse cleanup).
7. Run `uv run pytest tests/test_migrations.py -v`; expect PASS.
8. Run `uv run pytest -v`; expect all Day 1 + Day 2 suites PASS.

---

## Day 2 Definition of Done
1. `uv run pytest -v` passes 100% with zero warnings on `taskqueue_test`.
2. `uv run alembic upgrade head` produces the three tables with correct FKs on both databases.
3. Only the Day 2 files listed above changed; `app/tasks/scoring.py` remains untouched.
4. No secrets, no untracked junk; working state ready for the owner to review and commit on a feature branch.
