# Milestone 1 Backend Implementation Plan (1-Week Cadence, <4h/Day)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Milestone 1 FastAPI backend on MySQL 8: student accounts with usernames, full course CRUD with color badges, owner-scoped task CRUD with optional course association, and dual queue sorting (deadline + smart score) with explainable priority breakdown.

**Architecture:** Feature-based modular structure (`auth/`, `users/`, `courses/`, `tasks/`) backed by shared `core/` (config, database, security). Routers handle HTTP parsing, services enforce SQL-level ownership boundaries, and `tasks/scoring.py` is a pure mathematical priority engine with zero DB/framework dependencies. Alembic manages the MySQL 8 schema; tests run against an isolated `taskqueue_test` database.

**Tech Stack:** Python 3.12 (uv), FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync), PyMySQL + cryptography, Alembic, pydantic-settings, PyJWT, pwdlib[argon2], email-validator, pytest, httpx.

**Spec:** `feature/2026-11-17-milestone-1-backend` (`feature/2026-11-17-milestone-1-backend/specification.md`, `feature/2026-11-17-milestone-1-backend/implementation.md`, `feature/2026-11-17-milestone-1-backend/validation.md`), governed by `constitution.md` and `tech-stack.md`.

---

## 1-Week Schedule Breakdown (<4 Hours Coding / Day)

| Day | Focus Area | Tasks Included | Est. Time | Deliverable |
|---|---|---|---|---|
| **Day 1** | Foundation & Priority Math | **Task 1** (Scaffold & DB Core) + **Task 2** (Pure Scoring Engine) | ~3.0 hrs | Working project config, UTC types, and 100% unit-tested scoring algorithms. |
| **Day 2** | Database Models & Migrations | **Task 3** (User, Course, Task Models, Alembic Migration, MySQL Test Harness) | ~2.5 hrs | MySQL schema migrated, cascade rules in place, guarded test suite running. |
| **Day 3** | Authentication & Users | **Task 4** (Security, JWT Auth, Register/Login by Username/Email, `/users/me`) | ~2.5 hrs | Working student registration, flexible login, and profile lifecycle. |
| **Day 4** | Academic Domain CRUD | **Task 5** (Course CRUD) + **Task 6** (Task CRUD with Course Linkage) | ~3.5 hrs | Full course management with color badges and task creation with priority math. |
| **Day 5** | Queue Engine & Delivery | **Task 7** (Queue & Top Tasks) + **Task 8** (IDOR Security, Swagger QA, Docs) | ~3.5 hrs | Functional dual queue (`?sort=deadline\|smart`), isolation verified, M1 complete. |
| **Days 6–7** | Buffer & Review | Manual testing, exploratory edge cases, and M2 handoff prep | — | Reserve time for unexpected blockers. |

---

## Global Constraints

- Python 3.12 via uv; every command runs as `uv run ...`. No global installs, no poetry/pip.
- MySQL 8 / InnoDB / utf8mb4 everywhere, including tests. No SQLite (Constitution D-1).
- Sync SQLAlchemy 2.0 only; all endpoints are plain `def` (no blocking calls inside `async def`).
- Every protected route depends strictly on `get_current_user` (Constitution S-1).
- Every query on user-owned data filters by `owner_id == current_user.id` in SQL (Constitution S-2). Missing and cross-user resources both return `404 {"detail": "<Resource> not found"}` (Constitution S-3).
- User credentials: Argon2 password hashing; JWT HS256 with `sub = str(user_id)`, expiration `ACCESS_TOKEN_EXPIRE_DAYS` (default 7). `SECRET_KEY` and `DATABASE_URL` required at startup (Constitution S-4).
- Floating-point columns use `sa.Double` (never 4-byte `sa.Float`). Datetimes use `UTCDateTime` (MySQL `DATETIME(fsp=6)`, UTC-aware). Inputs use Pydantic `AwareDatetime` (Constitution D-4).
- No score columns in database tables (Constitution D-5). `Base.metadata.create_all` is forbidden in production; tests also migrate via Alembic (Constitution D-2).
- Deleting a course sets `tasks.course_id = NULL` (`ON DELETE SET NULL`), preserving the student's task. Deleting a user cascades and removes all their courses and tasks (`ON DELETE CASCADE`).
- Scoring constants: `WEIGHT_TIME_PRESSURE = 0.50`, `WEIGHT_IMPACT = 0.35`, `WEIGHT_DIFFICULTY = 0.15`, `IMPACT_CAP_PERCENT = 50.0`, `URGENT_WINDOW_HOURS = 24.0`, default `daily_study_hours = 3.0`.
- Forbidden in M1: Docker, Redis, ML code, frontend/CORS, email sending, deployment configuration.
- Version control is handled by the owner per `../AGENTS.md` (no automated git commits without explicit instruction).

## Prerequisite (Owner Action, before Day 2)

Run the one-time MySQL setup SQL from `feature/2026-11-17-milestone-1-backend/implementation.md` §1 to create `taskqueue`, `taskqueue_test`, and the `taskqueue` MySQL user. Copy `../.env.example` to `../.env` and configure `SECRET_KEY`, `DATABASE_URL`, and `TEST_DATABASE_URL`.

## Review Focus

1. **Non-UTC due date offsets:** A student in UTC+8 sends `2026-11-20T23:59:00+08:00`. Expected: stored as exact instant, returned as `2026-11-20T15:59:00Z`. Test: `test_due_at_offset_is_returned_as_utc` (Task 6).
2. **Login flexibility:** Register with username `alex_dev` and email `Alex@School.edu`. Login with `alex_dev` OR `alex@school.edu` (case-insensitive). Test: `test_login_with_username_or_email` (Task 4).
3. **Cross-user course attachment (IDOR):** User B creates a task attempting to set `course_id = <User A's course ID>`. Expected: `404 Not Found`, not attached. Test: `test_create_task_with_foreign_course_is_404` (Task 6).
4. **Course deletion safety:** User deletes a course. Tasks linked to it must survive with `course_id = null`. Test: `test_deleting_course_sets_task_course_id_to_null` (Task 6).
5. **Token of deleted user:** Token issued before `DELETE /users/me`. Expected: `401 Unauthorized`. Test: `test_token_of_deleted_user_is_401` (Task 4).

---

## DAY 1: Foundation & Priority Math (~3.0 Hours)

### Task 1: Project scaffold, settings, and database core (~1.5 hrs)

**Files:**
- Create: `../pyproject.toml`, `.python-version`, `../uv.lock`, `../.env.example`
- Create: `app/__init__.py`, `app/core/__init__.py`, `../app/core/config.py`, `../app/core/database.py`
- Test: `tests/__init__.py`, `../tests/test_core.py`

**Interfaces:**
- Produces:
  - `app.core.config.Settings`: fields `secret_key: str`, `database_url: str`, `test_database_url: str | None = None`, `access_token_expire_days: int = 7`.
  - `app.core.config.get_settings() -> Settings`.
  - `app.core.database.Base(DeclarativeBase)`.
  - `app.core.database.UTCDateTime(TypeDecorator)` with `impl = mysql.DATETIME(fsp=6)`: aware datetime -> naive UTC on bind; naive UTC -> aware UTC on result.
  - `app.core.database.utcnow() -> datetime` (aware UTC).
  - `app.core.database.engine`, `SessionLocal`, `get_db() -> Iterator[Session]`, `DbSession`.

- [ ] **Step 1: Scaffold dependencies and project configuration**

Run: `uv init --bare --python 3.12`, `uv python pin 3.12`, then:
`uv add "fastapi[standard]" "sqlalchemy>=2.0" alembic pymysql cryptography pydantic-settings pyjwt "pwdlib[argon2]" email-validator` and `uv add --dev pytest httpx`.
Add pytest config to `../pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```
Create `../.env.example` with `SECRET_KEY=change-me`, `DATABASE_URL=mysql+pymysql://taskqueue:<pw>@localhost:3306/taskqueue?charset=utf8mb4`, `TEST_DATABASE_URL=mysql+pymysql://taskqueue:<pw>@localhost:3306/taskqueue_test?charset=utf8mb4`, `ACCESS_TOKEN_EXPIRE_DAYS=7`.

- [ ] **Step 2: Write failing unit tests in `../tests/test_core.py`**

Test that Settings requires `SECRET_KEY`, default expiry is 7, `UTCDateTime` converts timezone offsets to naive UTC, rejects naive datetimes on write, and returns aware UTC datetimes on read.

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_core.py -v`
Expected: FAIL (missing `app.core.config` / `app.core.database`).

- [ ] **Step 4: Implement `../app/core/config.py` and `../app/core/database.py`**

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_core.py -v`
Expected: PASS (all tests pass).

---

### Task 2: Pure priority engine (~1.5 hrs)

**Files:**
- Create: `app/tasks/__init__.py`, `../app/tasks/scoring.py`
- Test: `../tests/test_scoring.py`

**Interfaces:**
- Consumes: Nothing external (pure Python, standard library only).
- Produces:
  - `class SortMode(StrEnum)`: `deadline = "deadline"`, `smart = "smart"`.
  - `class ScorableTask(Protocol)`: `id: int`, `due_at: datetime`, `grade_weight: float`, `estimated_hours: float`, `difficulty: int`, `completed: bool`, `completed_at: datetime | None`.
  - `@dataclass(frozen=True) class PriorityResult`: `score: float`, `time_pressure: float`, `impact: float`, `difficulty_factor: float`, `hours_until_due: float`, `urgent: bool`, `overdue: bool`.
  - `compute_priority(task: ScorableTask, daily_study_hours: float, now: datetime) -> PriorityResult | None`.
  - `sort_tasks(tasks: Iterable[T], mode: SortMode, daily_study_hours: float, now: datetime) -> list[tuple[T, PriorityResult | None]]`.

- [ ] **Step 1: Write failing tests in `../tests/test_scoring.py`**

Test exact reference scores A=20.2, B=56.1, C=64.5 with frozen `now = 2026-11-17T12:00:00Z` and `daily_study_hours = 3.0`. Test boundary cases: 24h urgent cutoff, impact cap at 50%, difficulty factor 0 to 1, deadline sorting order, smart sorting order, completed tasks at the bottom with `None` priority.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scoring.py -v`
Expected: FAIL (ImportError `app.tasks.scoring`).

- [ ] **Step 3: Implement `../app/tasks/scoring.py`**

Implement formula per `feature/2026-11-17-milestone-1-backend/implementation.md` §4 and ordering per §4.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_scoring.py -v`
Expected: PASS.

---

## DAY 2: Database Models & Migration Harness (~2.5 Hours)

### Task 3: Models (Users, Courses, Tasks), initial Alembic migration, and MySQL test harness (~2.5 hrs)

**Files:**
- Create: `app/users/__init__.py`, `app/users/models.py`, `app/courses/__init__.py`, `app/courses/models.py`, `app/tasks/models.py`, `app/models.py`
- Create: `../alembic.ini`, `../alembic/env.py`, `../alembic/script.py.mako`, `alembic/versions/<rev>_create_users_courses_tasks.py`
- Test: `../tests/conftest.py`, `../tests/test_migrations.py`

**Interfaces:**
- Consumes: `Base`, `UTCDateTime`, `utcnow`, `get_settings` (Task 1).
- Produces:
  - `User`: `id`, `username: Mapped[str]` (VARCHAR 50, unique, indexed), `email: Mapped[str]` (VARCHAR 320, unique, indexed), `hashed_password`, `daily_study_hours` (Double), `created_at` (UTCDateTime). Relationships: `courses` and `tasks` with `cascade="all, delete-orphan", passive_deletes=True`.
  - `Course`: `id`, `owner_id` (FK `users.id` `ON DELETE CASCADE`), `name` (VARCHAR 100), `code` (VARCHAR 20), `color` (VARCHAR 7, default `"#3B82F6"`), `created_at`, `updated_at`. Relationship: `tasks` with `back_populates="course"`.
  - `TaskCategory(StrEnum)`: `quiz, homework, project, exam, other`.
  - `Task`: `id`, `owner_id` (FK `users.id` `ON DELETE CASCADE`), `course_id` (FK `courses.id` `ON DELETE SET NULL`, nullable), `title`, `description`, `category` (Enum VARCHAR 20 + Check), `due_at`, `grade_weight` (Double), `estimated_hours` (Double), `difficulty`, `completed`, `completed_at`, `created_at`, `updated_at`. Relationships: `owner`, `course`.
  - `../tests/conftest.py`: Guarded MySQL `test_engine` (must end with `_test`), running Alembic migrations once, auto-cleaning tables before each test (`DELETE FROM tasks; DELETE FROM courses; DELETE FROM users;`), `db_session`.

- [ ] **Step 1: Define models in `app/users/models.py`, `app/courses/models.py`, `app/tasks/models.py`, `app/models.py`**

- [ ] **Step 2: Write failing tests in `../tests/test_migrations.py`**

Verify tables `users`, `courses`, `tasks`, and `alembic_version` exist; verify foreign key constraints (`users.id` cascade delete, `courses.id` set null on tasks); verify `Double` types; verify downgrade and upgrade cycles.

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_migrations.py -v`
Expected: FAIL.

- [ ] **Step 4: Initialize Alembic and create migration**

Run `uv run alembic init alembic`, configure `env.py` to import `app.models`, generate initial revision:
`uv run alembic revision --autogenerate -m "create users courses and tasks"`.
Verify generated migration uses `DATETIME(fsp=6)`, `ON DELETE CASCADE`, `ON DELETE SET NULL`, and `sa.Double`. Run `uv run alembic upgrade head` on `taskqueue`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_migrations.py -v`
Expected: 5 passed.

---

## DAY 3: Authentication & Profile Service (~2.5 Hours)

### Task 4: Security, authentication, and `/users/me` (~2.5 hrs)

**Files:**
- Create: `app/core/security.py`, `app/users/schemas.py`, `app/users/router.py`, `app/auth/__init__.py`, `app/auth/router.py`, `app/auth/dependencies.py`, `app/main.py`
- Modify: `../tests/conftest.py` (add `client`, `make_user`, `auth_headers`)
- Test: `tests/test_auth.py`, `tests/test_users.py`

**Interfaces:**
- Consumes: `get_settings`, `DbSession`, `User` (Tasks 1, 3).
- Produces:
  - `security.hash_password`, `verify_password`, `create_access_token`, `decode_access_token`.
  - Schemas: `UserCreate(username, email, password)`, `UserRead(id, username, email, daily_study_hours, created_at)`, `UserUpdate(daily_study_hours)`, `Token(access_token, token_type)`.
  - `auth.dependencies.get_current_user -> User` (single auth gateway, S-1).
  - Routes: `POST /auth/register`, `POST /auth/login` (accepts email or username in `username` field), `GET /users/me`, `PATCH /users/me`, `DELETE /users/me`.
  - `app.main.app` FastAPI entrypoint.

- [ ] **Step 1: Write failing tests in `tests/test_auth.py` and `tests/test_users.py`**

Include Review Focus 2 (`test_login_with_username_or_email`) and Review Focus 5 (`test_token_of_deleted_user_is_401`), along with duplicate checks (409), password hashing security, and `/users/me` CRUD.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth.py tests/test_users.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement security, user schemas, auth routes, and user routes**

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_auth.py tests/test_users.py -v`
Expected: PASS.

---

## DAY 4: Academic Domain CRUD (~3.5 Hours)

### Task 5: Course management CRUD (`/courses`) (~1.5 hrs)

**Files:**
- Create: `app/courses/schemas.py`, `app/courses/service.py`, `app/courses/router.py`
- Modify: `app/main.py` (register courses router)
- Test: `tests/test_courses.py`

**Interfaces:**
- Consumes: `CurrentUser`, `DbSession`, `Course` (Tasks 1, 3, 4).
- Produces:
  - Schemas:
    - `CourseCreate`: `name` (1–100 chars), `code` (1–20 chars), `color: str = "#3B82F6"` (regex `^#[0-9A-Fa-f]{6}$`).
    - `CourseUpdate`: `name`, `code`, `color` (all optional).
    - `CourseRead`: `id`, `name`, `code`, `color`, `created_at`, `updated_at`.
  - `service.CourseNotFoundError`.
  - Service functions (filtered by `owner_id == user.id`):
    - `create_course(db, owner, data, now) -> Course`
    - `list_courses(db, owner) -> list[Course]`
    - `get_course(db, owner, course_id) -> Course`
    - `update_course(db, owner, course_id, data, now) -> Course`
    - `delete_course(db, owner, course_id) -> None`
  - Routes: `POST /courses`, `GET /courses`, `GET /courses/{id}`, `PATCH /courses/{id}`, `DELETE /courses/{id}`.

- [ ] **Step 1: Write failing tests in `tests/test_courses.py`**

Test course creation (201), listing returns user's courses, get by id, partial patch, hex color regex rejection (e.g. `"blue"` -> 422), and delete (204 then 404).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_courses.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement schemas, service, and router for courses**

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_courses.py -v`
Expected: PASS.

---

### Task 6: Task CRUD with optional course association (~2.0 hrs)

**Files:**
- Create: `app/tasks/schemas.py`, `app/tasks/service.py`, `app/tasks/router.py`
- Modify: `app/main.py` (register tasks router)
- Test: `tests/test_tasks_crud.py`

**Interfaces:**
- Consumes: `CurrentUser`, `DbSession`, `Task`, `Course`, `compute_priority` (Tasks 1–5).
- Produces:
  - Schemas:
    - `TaskCreate`: `title`, `description`, `course_id: int | None = None`, `category: TaskCategory`, `due_at: AwareDatetime`, `grade_weight: float`, `estimated_hours: float`, `difficulty: int`, `completed: bool = False`.
    - `TaskUpdate`: same fields, optional.
    - `CourseBrief`: `id: int`, `code: str`, `name: str`, `color: str`.
    - `PriorityRead`: priority breakdown and flags.
    - `TaskRead`: all task columns plus `course: CourseBrief | None` and `priority: PriorityRead | None`.
    - `TaskPage`: `items: list[TaskRead]`, `total: int`, `limit: int`, `offset: int`.
  - Service functions (validating `course_id` ownership when provided, raising 404 if invalid):
    - `create_task`, `get_task`, `update_task`, `delete_task`.
  - Routes: `POST /tasks`, `GET /tasks/{id}`, `PATCH /tasks/{id}`, `DELETE /tasks/{id}`.

- [ ] **Step 1: Write failing tests in `tests/test_tasks_crud.py`**

Include Review Focus 1 (`test_due_at_offset_is_returned_as_utc`), Review Focus 3 (`test_create_task_with_foreign_course_is_404`), Review Focus 4 (`test_deleting_course_sets_task_course_id_to_null`), field validation bounds, and completion toggles.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tasks_crud.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement task schemas, service, and router**

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tasks_crud.py -v`
Expected: PASS.

---

## DAY 5: Queue Engine & Delivery (~3.5 Hours)

### Task 7: Queue listing with course filter, deadline/smart sort, and top tasks (~2.0 hrs)

**Files:**
- Modify: `app/tasks/service.py`, `app/tasks/router.py`
- Test: `tests/test_tasks_queue.py`

**Interfaces:**
- Consumes: Tasks 2, 5, 6.
- Produces:
  - `service.list_tasks(db, owner, *, sort, course_id, category, completed, limit, offset, now)`. Filters `owner_id`, optional `course_id`, `category`, and `completed` in SQL; sorts with `sort_tasks`; slices pagination.
  - `service.top_tasks(db, owner, *, n, sort, now)`: top incomplete tasks.
  - Routes: `GET /tasks` (supports `?course_id=...&sort=deadline|smart`), `GET /tasks/top` (defaults to smart).

- [ ] **Step 1: Write failing tests in `tests/test_tasks_queue.py`**

Test deadline sort (default), smart sort, filtering by `course_id`, filtering by `category` and `completed`, pagination offset/limit, and top tasks endpoint.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tasks_queue.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement list_tasks and top_tasks in service and router**

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tasks_queue.py -v`
Expected: PASS.

---

### Task 8: Cross-tenant isolation suite, manual QA, and context record (~1.5 hrs)

**Files:**
- Create: `tests/test_isolation.py`, `specs/context.md`
- Test: full test suite (`uv run pytest -v`)

**Interfaces:**
- Consumes: Full API (Tasks 1–7).
- Produces: Security verification for Constitution S-2/S-3, Phase 4 living context documentation (`specs/context.md`).

- [ ] **Step 1: Write security isolation tests in `tests/test_isolation.py`**

Verify that User B accessing User A's course or task returns masked `404 Not Found`; User B cannot assign User A's course to their task (404); user listings never leak cross-tenant courses or tasks; deleting User A deletes their courses and tasks without affecting User B.

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 3: Execute manual QA in `/docs`**

Run `uv run fastapi dev app/main.py`. Test registration, course creation, task creation with and without course, deadline sort, smart sort, study hours adjustment, and account deletion.

- [ ] **Step 4: Create `specs/context.md`**

Document architecture, API contracts, local runbook, test execution summary, and M2 handoff.
