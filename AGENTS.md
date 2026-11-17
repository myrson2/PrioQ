# AGENTS.md — AI Agent Guidelines & Architecture Manual

> **Scope:** This document defines mandatory architectural invariants, technical patterns, and development guidelines for all AI agents working on the **Smart Student Task Prioritization Queue System**.

---

## 1. Prime Directives & Constitution Invariants

Every agent modifying this codebase MUST strictly abide by the rules ratified in [`specs/constitution.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/specs/constitution.md):

1. **Axiom 1 (Explainable Priority):** Every task priority score returned by the API must include its full factor breakdown (`time_pressure`, `impact`, `difficulty_factor`, `hours_until_due`, `urgent`, `overdue`). Never return an opaque, black-box score.
2. **Axiom 2 / S-3 (Privacy by Default & 404 Masking):** Cross-tenant access to another user's course or task MUST return `404 Not Found` identical to a nonexistent resource. Never return `403 Forbidden` for IDOR attempts, as it leaks resource existence.
3. **Axiom 3 (Pure Scoring Engine):** `app/tasks/scoring.py` must remain pure functions without database or web framework dependencies. Current time (`now`) must be injected to preserve deterministic testability.
4. **S-1 (Single Auth Gateway):** Every protected endpoint must resolve user identity solely through `app/auth/dependencies.py:get_current_user`. Never inspect headers or decode tokens inside individual route handlers.
5. **S-2 (Ownership in the Query):** Every query for user-owned resources must filter by `owner_id == current_user.id` directly in the SQL statement. Never fetch records first and check ownership in Python memory.
6. **D-1 (MySQL 8 Everywhere):** MySQL 8 / InnoDB / utf8mb4 is mandatory across development and testing. SQLite is strictly forbidden.
7. **D-2 (Migrations Only):** Never call `Base.metadata.create_all()` in production code. All schema evolution must be driven by Alembic migrations.
8. **D-3 (Cascading Deletes):** Deleting a user cascades all courses and tasks (`ON DELETE CASCADE`). Deleting a course sets `tasks.course_id = NULL` (`ON DELETE SET NULL`), preserving the student's task.
9. **D-4 (UTC Time Discipline):** All timestamps are stored in UTC `DATETIME(6)`. The API accepts only timezone-aware ISO 8601 strings (`AwareDatetime`) and rejects naive timestamps (`422 Unprocessable`).
10. **D-5 (Scores Never Persisted):** Priority scores change as deadlines approach; they must be computed dynamically on read and never stored in MySQL columns.

---

## 2. Command Palette & Tooling Rules

All commands MUST run through the **`uv`** package manager. Do not run bare `python`, `pip`, or `poetry`.

```bash
# Add dependencies
uv add "<package_name>"
uv add --dev "<package_name>"

# Run development server
uv run fastapi dev app/main.py

# Database migrations
uv run alembic revision --autogenerate -m "<description>"
uv run alembic upgrade head
uv run alembic downgrade -1

# Run tests
uv run pytest -v
uv run pytest tests/test_tasks_queue.py -v
```

---

## 3. Layer Boundaries & Architectural Conventions

```
Router (FastAPI)     -> HTTP parsing, dependency injection, status code mapping.
Service              -> SQL queries with owner_id filters, business logic, IDOR validation.
Scoring (Pure)       -> Mathematical formulas; pure Python; no DB imports.
Persistence (Models) -> Declarative SQLAlchemy models, foreign keys, cascade rules.
```

### Key Type & ORM Patterns
- **Floating numbers:** Always use `sqlalchemy.Double` (never `sa.Float`, which causes MySQL 4-byte float truncation).
- **Date/Time:** Always use `app.core.database.UTCDateTime` in models.
- **Strings:** Every `sa.String` must declare an explicit length (e.g. `String(200)`), required by MySQL VARCHAR.
- **Enums:** Store task categories with `sa.Enum(TaskCategory, native_enum=False, create_constraint=True, length=20)` to allow zero-downtime additions.
- **Sync Endpoints:** Use synchronous `def` endpoints with `DbSession` (`Annotated[Session, Depends(get_db)]`). Do not use `async def` for blocking SQLAlchemy database calls.

---

## 4. Testing Discipline

- **Test Database Isolation:** Tests run against `taskqueue_test`. The test engine in `tests/conftest.py` will abort if the database name does not end in `_test`.
- **Clean State:** An autouse fixture truncates tables before each test (`DELETE FROM tasks; DELETE FROM courses; DELETE FROM users;`).
- **TDD Requirement:** When adding new features or fixing bugs, always write failing unit/integration tests before writing implementation code.
- **Zero Warnings:** Keep tests clean and deterministic; avoid flaky time comparisons by injecting fixed reference timestamps.

---

## 5. Milestone Scope Discipline

When implementing Milestone 1, agents are **strictly forbidden** from introducing:
- Docker / Dockerfiles / Docker Compose.
- Redis, Celery, or background worker processes.
- Machine Learning models, Scikit-Learn, or Pandas.
- Frontend React code or CORS wildcards.
- Email delivery services or password reset email flows.
- Production deployment or cloud hosting scripts.
