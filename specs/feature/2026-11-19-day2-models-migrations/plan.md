# Day 2 Execution Plan — Database Models & Migration Harness (~2.5h)

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`. Implement task-by-task; track with `- [ ]` checkboxes.

**Goal:** Build the M1 persistence layer: three owner-scoped MySQL 8 tables, one Alembic revision, and a guarded test harness with schema verification.
**Architecture:** Feature modules (`users/`, `courses/`, `tasks/`) define declarative models; `app/models.py` aggregates them for Alembic; `app/core/database.py` (Day 1) supplies `Base`, `UTCDateTime`, `utcnow`, and engine/session helpers. No routers today.
**Tech Stack:** Python 3.12 (uv), SQLAlchemy 2.0 sync, Alembic, PyMySQL, pytest, MySQL 8 / InnoDB / `utf8mb4`.
**Spec:** `specs/feature/2026-11-19-day2-models-migrations/` (`specification.md`, `implementation.md`, `validation.md`). Day 1 is assumed complete; no verification gate is included.

---

### Schedule
| Day | Focus Area | Tasks Included | Est. Time | Deliverable |
|---|---|---|---|---|
| **Day 2** | Persistence & migrations | Task 3 (models, initial Alembic revision, MySQL test harness) | ~2.5 hrs | Migrated MySQL schema, cascade rules verified, guarded test suite green. |

### Global Constraints
- All commands via `uv run`; no global installs. Sync SQLAlchemy only.
- MySQL 8 / InnoDB / `utf8mb4` including tests; SQLite forbidden (D-1). No `create_all` (D-2).
- Floating columns: `sa.Double` only. Timestamps: `UTCDateTime`. Strings: explicit lengths (D-4, D-6).
- Category enum: `native_enum=False, create_constraint=True, length=20`.
- Every user-owned table has `ON DELETE CASCADE` to `users.id`; `tasks.course_id` uses `ON DELETE SET NULL` (D-3).
- Test DB name must end in `_test`; autouse cleanup before each test.
- No priority columns (D-5), no routers, no commits to git.

### Prerequisite — readiness check (owner action if it fails)
Confirm `DATABASE_URL` / `TEST_DATABASE_URL` in `.env` point at existing `taskqueue` / `taskqueue_test` databases and that the dedicated MySQL user can connect:
```bash
uv run python -c "from app.core.config import get_settings; from sqlalchemy import create_engine, text; from sqlalchemy.engine import make_url; s=get_settings(); u=make_url(s.test_database_url); assert u.database and u.database.endswith('_test'), u.database; print(create_engine(s.test_database_url).scalar(text('SELECT DATABASE()')))"
```
Expected: prints `taskqueue_test`. If it fails, create both databases and grant privileges per `implementation.md` §1, then re-run.

### Review Focus
1. **Non-test DB guard** — wrong `TEST_DATABASE_URL` aborts: `test_test_database_name_is_guarded`.
2. **User cascade** — deleting a user removes their courses/tasks: `test_foreign_keys_use_cascade_and_set_null`.
3. **Course disassociation** — deleting a course nulls `tasks.course_id`: same test.
4. **Type fidelity** — `DOUBLE` and `DATETIME(6)`: `test_double_and_datetime_columns`.
5. **Migration reversibility** — downgrade then upgrade: `test_upgrade_downgrade_cycle`.

---

### Task 3: Models, initial migration, and MySQL test harness (~2.5 hrs)

**Files:**
- Create: `app/users/__init__.py`, `app/users/models.py`, `app/courses/__init__.py`, `app/courses/models.py`, `app/tasks/models.py`, `app/models.py`
- Create: `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/<rev>_create_users_courses_tasks.py`
- Test: `tests/conftest.py`, `tests/test_migrations.py`

**Interfaces:**
- Consumes: `app.core.database.Base`, `UTCDateTime`, `utcnow`; `app.core.config.get_settings` (Task 1).
- Produces: `app.users.models.User`, `app.courses.models.Course`, `app.tasks.models.Task`, `app.tasks.models.TaskCategory`; `app.models` import aggregator; initial Alembic revision; `tests/conftest.py` fixtures `test_engine`, `db_session`; `tests/test_migrations.py`.

- [ ] **Step 1:** Implement the three model modules and `app/models.py` aggregator (FR-1…FR-3).
- [ ] **Step 2:** Write failing tests in `tests/test_migrations.py` for FR-4…FR-6 and all five Review Focus cases.
- [ ] **Step 3:** Run `uv run pytest tests/test_migrations.py -v`; confirm failure (no migration/harness).
- [ ] **Step 4:** Run `uv run alembic init alembic`, wire `env.py` to `get_settings().database_url` + `app.models`, then `uv run alembic revision --autogenerate -m "create users courses and tasks"`. Verify native MySQL DDL, `DOUBLE`, `DATETIME(6)`, both FK actions. Apply with `uv run alembic upgrade head`.
- [ ] **Step 5:** Implement `tests/conftest.py` (guard, session-scoped upgrade, autouse cleanup, `db_session`).
- [ ] **Step 6:** Run `uv run pytest tests/test_migrations.py -v`; expect all tests pass.
- [ ] **Step 7:** Run `uv run pytest -v` to confirm Day 1 suites remain green.

**Definition of Done:** schema migrated on `taskqueue` and `taskqueue_test`, all migration tests pass, full suite green, only Day 2 files changed.
