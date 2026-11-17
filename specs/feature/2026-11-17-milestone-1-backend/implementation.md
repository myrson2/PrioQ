# Milestone 1 Backend — Implementation

**Feature folder:** `specs/feature/2026-11-17-milestone-1-backend/` · **Milestone:** M1 (see `specs/roadmap.md`) · **Governed by:** `specs/constitution.md`

## 1. Stack & Tooling
- Python **3.12** managed via **uv** (`pyproject.toml` + `uv.lock`).
- Dependencies: `fastapi[standard]`, `sqlalchemy>=2.0`, `alembic`, `pymysql`, `cryptography`, `pydantic-settings`, `pyjwt`, `pwdlib[argon2]`, `email-validator`. Dev: `pytest`, `httpx`.
- Engine: MySQL 8 (InnoDB, utf8mb4) with `pool_pre_ping=True`.

## 2. Architectural Boundaries & Project Layout
```
app/
  main.py                 # FastAPI app, registers all routers
  core/
    config.py             # Settings (SECRET_KEY, DATABASE_URL, ACCESS_TOKEN_EXPIRE_DAYS)
    database.py           # engine, SessionLocal, Base, get_db, UTCDateTime type
    security.py           # hash_password, verify_password, create_access_token, decode_access_token
  auth/
    router.py             # /auth/register, /auth/login
    dependencies.py       # get_current_user (single auth gateway)
  users/
    models.py             # User
    schemas.py            # UserCreate, UserRead, UserUpdate, Token
    router.py             # /users/me (GET, PATCH, DELETE)
  courses/
    models.py             # Course
    schemas.py            # CourseCreate, CourseUpdate, CourseRead
    service.py            # Course persistence and ownership verification
    router.py             # /courses (CRUD)
  tasks/
    models.py             # Task, TaskCategory enum
    schemas.py            # TaskCreate, TaskUpdate, TaskRead, PriorityRead, TaskPage, SortMode
    scoring.py            # Pure function priority engine (no DB, no FastAPI)
    service.py            # Task persistence, course ownership check, scoring integration
    router.py             # /tasks (CRUD, queue, top)
alembic/                  # env.py, versions/
tests/
  conftest.py             # MySQL test harness, auto-cleaning tables, client, auth fixtures
  test_scoring.py  test_auth.py  test_users.py  test_courses.py  test_tasks_crud.py  test_tasks_queue.py  test_isolation.py  test_migrations.py
```

## 3. Database Schema (MySQL 8, InnoDB, utf8mb4)

### `users`
| Column | Type | Constraints |
|---|---|---|
| `id` | INT | Primary Key, Auto-increment |
| `username` | VARCHAR(50) | Unique, Not Null, Indexed |
| `email` | VARCHAR(320) | Unique, Not Null, Indexed (stored lowercase) |
| `hashed_password` | VARCHAR(255) | Not Null |
| `daily_study_hours` | DOUBLE | Not Null, Default: 3.0 (Allowed: 0.5–16.0) |
| `created_at` | DATETIME(6) | Not Null, UTC |

### `courses`
| Column | Type | Constraints |
|---|---|---|
| `id` | INT | Primary Key, Auto-increment |
| `owner_id` | INT | Foreign Key (`users.id` `ON DELETE CASCADE`), Indexed, Not Null |
| `name` | VARCHAR(100) | Not Null (e.g. "Software Engineering") |
| `code` | VARCHAR(20) | Not Null (e.g. "CS 401") |
| `color` | VARCHAR(7) | Not Null, Default: "#3B82F6" (Regex: `^#[0-9A-Fa-f]{6}$`) |
| `created_at` | DATETIME(6) | Not Null, UTC |
| `updated_at` | DATETIME(6) | Not Null, UTC |

### `tasks`
| Column | Type | Constraints |
|---|---|---|
| `id` | INT | Primary Key, Auto-increment |
| `owner_id` | INT | Foreign Key (`users.id` `ON DELETE CASCADE`), Indexed, Not Null |
| `course_id` | INT | Foreign Key (`courses.id` `ON DELETE SET NULL`), Indexed, Nullable |
| `title` | VARCHAR(200) | Not Null, Stripped (1–200 chars) |
| `description` | TEXT | Nullable (Max 2000 chars) |
| `category` | VARCHAR(20) | Not Null, Check Constraint: `quiz, homework, project, exam, other` |
| `due_at` | DATETIME(6) | Not Null, UTC |
| `grade_weight` | DOUBLE | Not Null (0.0–100.0) |
| `estimated_hours` | DOUBLE | Not Null (>0.0, ≤500.0) |
| `difficulty` | INT | Not Null (1–5) |
| `completed` | TINYINT(1) | Not Null, Default: 0 |
| `completed_at` | DATETIME(6) | Nullable |
| `created_at` | DATETIME(6) | Not Null, UTC |
| `updated_at` | DATETIME(6) | Not Null, UTC |

## 4. Priority Engine (`tasks/scoring.py`)
Remains pure with injected `now: datetime` and `daily_study_hours: float`:
```
hours_until_due  = (due_at - now) in hours
if hours_until_due <= 0:
    time_pressure = 1.0
else:
    available     = (hours_until_due / 24) * daily_study_hours
    time_pressure = min(estimated_hours / available, 1.0)

impact            = min(grade_weight / 50.0, 1.0)
difficulty_factor = (difficulty - 1) / 4.0
score             = 100.0 * (0.50*time_pressure + 0.35*impact + 0.15*difficulty_factor)
overdue           = hours_until_due < 0
urgent            = hours_until_due <= 24.0
```
Completed tasks return `None` for priority.

## 5. API Endpoints
All protected endpoints require `Authorization: Bearer <token>`.

| Route | Method | Body / Query | Success | Errors |
|---|---|---|---|---|
| `/auth/register` | POST | `UserCreate(username, email, password)` | 201 `UserRead` | 409, 422 |
| `/auth/login` | POST | OAuth2 Form (`username` [email or username], `password`) | 200 `{access_token, token_type}` | 401 |
| `/users/me` | GET | — | 200 `UserRead` | 401 |
| `/users/me` | PATCH | `{daily_study_hours}` | 200 `UserRead` | 401, 422 |
| `/users/me` | DELETE | — | 204 | 401 |
| `/courses` | POST | `CourseCreate(name, code, color?)` | 201 `CourseRead` | 401, 422 |
| `/courses` | GET | — | 200 `list[CourseRead]` | 401 |
| `/courses/{id}` | GET | — | 200 `CourseRead` | 401, 404 |
| `/courses/{id}` | PATCH | `CourseUpdate(name?, code?, color?)` | 200 `CourseRead` | 401, 404, 422 |
| `/courses/{id}` | DELETE | — | 204 | 401, 404 |
| `/tasks` | POST | `TaskCreate(..., course_id?)` | 201 `TaskRead` | 401, 404 (bad course), 422 |
| `/tasks` | GET | `sort, course_id, category, completed, limit, offset` | 200 `TaskPage` | 401, 422 |
| `/tasks/top` | GET | `n=3, sort=smart` | 200 `list[TaskRead]` | 401, 422 |
| `/tasks/{id}` | GET | — | 200 `TaskRead` | 401, 404 |
| `/tasks/{id}` | PATCH | `TaskUpdate(..., course_id?)` | 200 `TaskRead` | 401, 404, 422 |
| `/tasks/{id}` | DELETE | — | 204 | 401, 404 |
