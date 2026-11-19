# Day 2 — Database Models & Migration Harness — Specification

**Feature folder:** `specs/feature/2026-11-19-day2-models-migrations/`  
**Milestone:** M1 (see [`specs/roadmap.md`](specs/roadmap.md))  
**Governed by:** [`specs/constitution.md`](specs/constitution.md) and [`specs/tech-stack.md`](specs/tech-stack.md)

---

## 1. Context & Motivation
Day 1 delivered typed settings, the `UTCDateTime` type decorator, the SQLAlchemy engine/session harness, and the pure scoring engine. Nothing persists yet. Day 2 establishes the MySQL 8 persistence layer — `users`, `courses`, `tasks` — through Alembic, plus a guarded test database harness that makes every later test deterministic. Day 3 (auth) and Day 4 (CRUD) depend entirely on these tables and ownership foreign keys.

## 2. Approaches Considered & Decision
- **Approach 1 (Single `tasks` table with a string category):** rejected — no place for course metadata or color badges, and no clean way to express course disassociation without destroying tasks.
- **Approach 2 (Three tables — SELECTED):** `users`, `courses`, `tasks` with optional `tasks.course_id`. Mirrors a student's semester, supports general non-course tasks, and enforces D-3 with `ON DELETE CASCADE` for user-owned rows and `ON DELETE SET NULL` for course deletion.
- **Approach 3 (Generic EAV / JSON blob schema):** rejected — loses database-level type and constraint enforcement, contradicts D-6.

## 3. Goals, Non-goals, and Anti-goals
### Goals
- Declarative models for `User`, `Course`, `Task`, and `TaskCategory`.
- One native-MySQL Alembic revision creating all tables, indexes, check constraints, and cascades.
- Guarded `taskqueue_test` harness: refuse any database whose name does not end in `_test`.
- Alembic-driven upgrade/downgrade verification on a real MySQL 8 test database.
### Non-goals
- Auth endpoints, JWT logic, user routers, course/task routers (Day 3+).
- Any change to `app/tasks/scoring.py` (Day 1 output is frozen).
- Frontend, Docker, Redis, Celery, ML, email, deployment config.
### Anti-goals
- No `Base.metadata.create_all()` against any real database (D-2).
- No priority-score columns (D-5); no naive datetimes (D-4); no SQLite (D-1).

## 4. User Stories
- **US-1 Schema Exists:** GIVEN a fresh MySQL 8 database WHEN `uv run alembic upgrade head` runs THEN `users`, `courses`, `tasks`, and `alembic_version` exist with the declared constraints.
- **US-2 Ownership Cascade:** GIVEN a user with courses and tasks WHEN that user is deleted THEN all their courses and tasks are removed by the database.
- **US-3 Safe Course Deletion:** GIVEN a course with linked tasks WHEN the course is deleted THEN linked tasks survive with `course_id = null`.
- **US-4 Type Integrity:** GIVEN the schema WHEN inspected THEN floats are `DOUBLE`, timestamps are `DATETIME(6)`, and every string column has an explicit length.
- **US-5 Test Safety:** GIVEN a misconfigured `TEST_DATABASE_URL` pointing at a non-`_test` database WHEN the test harness starts THEN it aborts before any destructive SQL.

## 5. Functional Requirements
- **FR-1 `User` model** (`app/users/models.py`): `id`, `username` VARCHAR(50) unique/indexed, `email` VARCHAR(320) unique/indexed, `hashed_password` VARCHAR(255), `daily_study_hours` `Double` default 3.0, `created_at` `UTCDateTime`. ORM relationships `courses`/`tasks` with `cascade="all, delete-orphan", passive_deletes=True`.
- **FR-2 `Course` model** (`app/courses/models.py`): `id`, `owner_id` FK `users.id ON DELETE CASCADE` indexed, `name` VARCHAR(100), `code` VARCHAR(20), `color` VARCHAR(7) default `#3B82F6`, `created_at`, `updated_at`.
- **FR-3 `Task` model** (`app/tasks/models.py`): `id`, `owner_id` FK `users.id ON DELETE CASCADE` indexed, `course_id` FK `courses.id ON DELETE SET NULL` nullable/indexed, `title` VARCHAR(200), `description` TEXT nullable, `category` `sa.Enum(TaskCategory, native_enum=False, create_constraint=True, length=20)`, `due_at` `UTCDateTime`, `grade_weight` `Double`, `estimated_hours` `Double`, `difficulty` Integer, `completed` Boolean default false, `completed_at` `UTCDateTime` nullable, `created_at`, `updated_at`.
- **FR-4 Initial migration** (`alembic/versions/<rev>_create_users_courses_tasks.py`): native MySQL DDL, `sa.Double`, `DATETIME(fsp=6)`, naming convention from `Base.metadata`, FKs with the two cascade behaviours above.
- **FR-5 Test harness** (`tests/conftest.py`): parse `TEST_DATABASE_URL` with `make_url`, assert `database.endswith("_test")`, run Alembic once per session, autouse fixture deletes from `tasks`, `courses`, `users` before each test.
- **FR-6 Schema tests** (`tests/test_migrations.py`): table existence, FK cascade actions, `Double`/`DATETIME(6)` types, database-name guard, and upgrade→downgrade→upgrade cycle.

## 6. Non-Functional Requirements
- **Security:** no credentials in docs, tests, or logs; dedicated `taskqueue` MySQL user only.
- **Data integrity:** MySQL 8 / InnoDB / `utf8mb4` everywhere (D-1); migrations only (D-2).
- **Time discipline:** all date columns use the Day 1 `UTCDateTime` decorator (D-4).
- **Tooling:** every command via `uv run`; no bare `python`/`pip`.

## 7. Acceptance Criteria Checklist
- [ ] `uv run alembic upgrade head` creates all four tables on `taskqueue`.
- [ ] `users.id` FKs cascade; `courses.id` FKs set null.
- [ ] Float columns are `DOUBLE`; timestamps are `DATETIME(6)`.
- [ ] `tests/conftest.py` aborts on a non-`_test` database name.
- [ ] `uv run pytest tests/test_migrations.py -v` passes on `taskqueue_test`.
- [ ] `uv run alembic downgrade base && uv run alembic upgrade head` succeeds.
