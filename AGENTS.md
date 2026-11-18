# AGENTS.md — AI Agent Guidelines & Architecture Manual

> **Scope:** This document defines mandatory rules, behavioral guidelines, architectural invariants, and technical patterns for all AI agents working on the **Smart Student Task Prioritization Queue System**.

---

## 1. Project Rules for AI Assistants

### Git rules
- NEVER commit or push directly to `main`. Always work on a feature branch.
- Branch names: `feature/<short-name>`, `fix/<short-name>`, `chore/<short-name>`.
- NEVER commit, push, merge, rebase, or force-push unless I ask you to.
- NEVER use `git push --force`, `git reset --hard`, or delete branches without asking.
- Keep commits small, with one purpose each. Message format: `type(scope): short description` (e.g. `feat(auth): add session logout`).
- Do not mix unrelated changes in the same commit or PR.

### Files you must never commit or print
- `.env`, secrets, API keys, passwords, tokens, database dumps, credentials.
- `.idea/`, `.vscode/`, `__pycache__/`, `*.pyc`, `.venv/`, `*.sqlite`, log files.
- If you see a secret in the code, stop and warn me instead of copying it anywhere.
- If a file that should be ignored is not in `.gitignore`, tell me before adding it.

### Before you change anything
- **NEVER write or modify code unless I explicitly say so.** This includes source files, tests, stubs, scaffolding, and config edits. If a task seems to need code, explain the plan and wait for my explicit approval first. Documentation edits I was asked to make are allowed.
- Read the relevant files first. Do not guess how the code works.
- If the request is unclear, ask a question instead of assuming.
- For changes touching more than 3 files, or anything involving the database, auth, or payments, explain your plan first and wait for my OK.
- Do not refactor, rename, or reformat code I did not ask you to touch.

### Code rules
- Follow the existing structure and naming of the project. Do not introduce a new pattern without telling me why.
- Do not add a new library or dependency without asking.
- Do not add abstractions "just in case". Keep it simple.
- Add type hints and short docstrings to new functions.
- No hardcoded secrets, URLs, or magic numbers. Use config or environment variables.
- No leftover debug code: no stray `print()`, commented-out blocks, or TODOs without a reason.
- Keep routes thin. Put business logic in services and database access in the persistence layer.

### Database rules
- NEVER edit the database schema by hand. Use Alembic migrations.
- NEVER drop tables, delete data, or run destructive SQL without my explicit approval.
- Always use parameterized queries or the ORM. Never build SQL with string concatenation.
- Wrap multi-step changes (like stock + order updates) in a transaction.

### Security rules
- Validate all input with Pydantic. Never trust the frontend or client.
- Check authentication and permissions on every protected endpoint.
- Never return password hashes or other sensitive fields in API responses.
- Do not log secrets, tokens, or personal data.

### Testing rules
- New features and bug fixes need pytest tests, including failure cases.
- Run the tests before saying the work is done. If you cannot run them, say so.
- Do not delete, skip, or weaken a test just to make it pass.
- A successful HTTP 200 does not prove the business logic is correct. Test the actual rules.

### Honesty and communication
- Never claim something works if you did not run or verify it.
- If you are unsure, say so. Do not invent functions, libraries, or APIs.
- Tell me what you changed, which files, and why, in simple words.
- Point out risks or problems you notice, even if I did not ask.
- If you make a mistake, say so and fix it. Do not hide it.

### Documentation
- Update the README or docs when behavior or setup changes.
- Document important decisions and their trade-offs in short notes.

### Definition of done
A task is done only when: the code works, tests pass, no secrets or junk files are staged, the diff only contains what was asked, and I have been told what changed.

---

## 2. Prime Directives & Constitution Invariants

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

## 3. Command Palette & Tooling Rules

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

## 4. Layer Boundaries & Architectural Conventions

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

## 5. Testing Discipline

- **Test Database Isolation:** Tests run against `taskqueue_test`. The test engine in `tests/conftest.py` will abort if the database name does not end in `_test`.
- **Clean State:** An autouse fixture truncates tables before each test (`DELETE FROM tasks; DELETE FROM courses; DELETE FROM users;`).
- **TDD Requirement:** When adding new features or fixing bugs, always write failing unit/integration tests before writing implementation code.
- **Zero Warnings:** Keep tests clean and deterministic; avoid flaky time comparisons by injecting fixed reference timestamps.

---

## 6. Milestone Scope Discipline

When implementing Milestone 1, agents are **strictly forbidden** from introducing:
- Docker / Dockerfiles / Docker Compose.
- Redis, Celery, or background worker processes.
- Machine Learning models, Scikit-Learn, or Pandas.
- Frontend React code or CORS wildcards.
- Email delivery services or password reset email flows.
- Production deployment or cloud hosting scripts.
