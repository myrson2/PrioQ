# Day 1 Execution Brief: Foundation & Priority Engine

**Feature Folder:** `specs/feature/2026-11-17-milestone-1-backend/`  
**Assignee:** Backend Engineer  
**Role:** Tech Lead / Senior Architect  
**Time Budget:** ~3.0 Hours (Strict hard cap: < 4.0 Hours)  
**Governing Documents:** [`specs/constitution.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/specs/constitution.md), [`AGENTS.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/AGENTS.md)

---

## Lead Architect's Note

Welcome to Day 1. Today we lay down the technical bedrock for Milestone 1. We have two non-negotiable goals to deliver before the end of the day:
1. **Scaffold our toolchain, typed environment configuration, and our custom UTC database type.**
2. **Build the pure mathematical priority engine with deterministic test coverage.**

Do not cut corners on testing. We follow strict Test-Driven Development (TDD). Write the failing tests first, observe the expected failure, implement the minimal solution, and verify. Do not commit code to `main`. Keep git commits clean and atomic.

---

## Task 1: Environment Scaffolding, Typed Settings & Database Core (~1.5 hrs)

### Objective
Scaffold the Python 3.12 project using `uv`. Establish typed configuration using `pydantic-settings` and configure SQLAlchemy's connection harness. Implement a custom `UTCDateTime` TypeDecorator to guarantee strict UTC discipline across MySQL.

### Architectural Invariants & Constraints
- **Tooling:** All commands MUST execute via `uv run`. Never use raw `pip` or global environments.
- **Database Engine:** MySQL 8 with `pool_pre_ping=True` to prevent stale connection drops. SQLite is strictly forbidden (Constitution D-1).
- **Time Discipline:** MySQL `DATETIME` stores no timezone information. Our custom `UTCDateTime` must ensure that data written to the database is converted to naive UTC, and data read back is always tagged with timezone-aware UTC (`datetime.timezone.utc`).

### Files to Create
- `pyproject.toml`, `.python-version`, `.env.example`
- `app/__init__.py`, `app/core/__init__.py`
- `app/core/config.py`
- `app/core/database.py`
- `tests/__init__.py`, `tests/test_core.py`

### Specification & Interface Requirements
1. **`app.core.config.Settings` (Pydantic BaseSettings):**
   - Required fields: `secret_key: str`, `database_url: str`.
   - Optional fields: `test_database_url: str | None = None`, `access_token_expire_days: int = 7`.
   - Configuration: read from `.env` file, ignore extra variables.
   - Cached accessor: `get_settings() -> Settings` using `@functools.lru_cache`.
2. **`app.core.database.UTCDateTime` (SQLAlchemy TypeDecorator):**
   - Base implementation: `sqlalchemy.dialects.mysql.DATETIME(fsp=6)`.
   - `process_bind_param(value, dialect)`: Accepts timezone-aware `datetime`. Converts to naive UTC. Rejects naive `datetime` with `ValueError`. Passes `None` through untouched.
   - `process_result_value(value, dialect)`: Reads naive UTC `datetime` from MySQL and attaches `timezone.utc`.
3. **Database Harness:**
   - Declarative base class `Base`.
   - Utility `utcnow() -> datetime` returning aware UTC timestamp.
   - Engine initialization using `get_settings().database_url` with `pool_pre_ping=True`.
   - Session maker `SessionLocal` (`expire_on_commit=False`).
   - FastAPI dependency `get_db() -> Iterator[Session]`.

### Edge Cases You Must Cover in `tests/test_core.py`
- [ ] **Missing Secret Key:** Instantiating `Settings` without `SECRET_KEY` must raise a Pydantic `ValidationError`.
- [ ] **Default Token Expiry:** Omitting `ACCESS_TOKEN_EXPIRE_DAYS` must default to exactly `7`.
- [ ] **Non-UTC Offset Normalization:** Passing a datetime with `+08:00` offset to `UTCDateTime.process_bind_param` must accurately subtract 8 hours and return naive UTC.
- [ ] **Naive Datetime Rejection:** Passing a naive datetime (where `tzinfo is None`) to `process_bind_param` must raise `ValueError`. Never silently assume local time.
- [ ] **Awareness on Read:** Reading a value via `process_result_value` must return a datetime where `result.tzinfo == timezone.utc`.
- [ ] **Null Safety:** Passing `None` to bind or result hooks must return `None` without raising `AttributeError`.

### Step-by-Step Execution Plan
1. Run `uv init --bare --python 3.12` and pin python to 3.12.
2. Add production dependencies: `fastapi[standard]`, `sqlalchemy>=2.0`, `alembic`, `pymysql`, `cryptography`, `pydantic-settings`, `pyjwt`, `pwdlib[argon2]`, `email-validator`.
3. Add development dependencies: `pytest`, `httpx`.
4. Configure `pyproject.toml` with `[tool.pytest.ini_options]` setting `testpaths = ["tests"]` and `pythonpath = ["."]`.
5. Create `.env.example` declaring `SECRET_KEY`, `DATABASE_URL`, `TEST_DATABASE_URL`, and `ACCESS_TOKEN_EXPIRE_DAYS`.
6. Write failing unit tests covering all listed edge cases in `tests/test_core.py`.
7. Execute `uv run pytest tests/test_core.py -v` and confirm tests fail as expected.
8. Implement `app/core/config.py` and `app/core/database.py`.
9. Re-run tests and confirm all 6 test cases pass.

---

## Task 2: Pure Priority Engine & Queue Ordering (~1.5 hrs)

### Objective
Implement the mathematical priority scoring algorithm and queue sorting logic in `app/tasks/scoring.py`. This is the core intellectual property of our backend.

### Architectural Invariants & Constraints
- **Purity Axiom (Constitution Axiom 3):** This module must be 100% pure Python. Do NOT import SQLAlchemy, FastAPI, or database sessions. Current time (`now`) must be injected as an argument to ensure deterministic testability.
- **Explainability Axiom (Constitution Axiom 1):** Priority cannot be a single opaque float. Every calculation must return its constituent breakdown (`time_pressure`, `impact`, `difficulty_factor`, `hours_until_due`, `urgent`, `overdue`).

### Files to Create
- `app/tasks/__init__.py`
- `app/tasks/scoring.py`
- `tests/test_scoring.py`

### Specification & Mathematical Formula
Implement:
1. `class SortMode(StrEnum)`: `deadline = "deadline"`, `smart = "smart"`.
2. `class ScorableTask(Protocol)`: Defines task attributes (`id: int`, `due_at: datetime`, `grade_weight: float`, `estimated_hours: float`, `difficulty: int`, `completed: bool`, `completed_at: datetime | None`).
3. `@dataclass(frozen=True) class PriorityResult`: Contains `score`, `time_pressure`, `impact`, `difficulty_factor`, `hours_until_due`, `urgent`, `overdue`.
4. **Formula Constants:**
   - `WEIGHT_TIME_PRESSURE = 0.50`
   - `WEIGHT_IMPACT = 0.35`
   - `WEIGHT_DIFFICULTY = 0.15`
   - `IMPACT_CAP_PERCENT = 50.0`
   - `URGENT_WINDOW_HOURS = 24.0`
5. **Formulas:**
   $$\text{hours\_until\_due} = \frac{(\text{due\_at} - \text{now})\text{ in seconds}}{3600}$$
   $$\text{available\_study\_hours} = \left(\frac{\text{hours\_until\_due}}{24}\right) \times \text{daily\_study\_hours}$$
   $$\text{time\_pressure} = \begin{cases} 1.0 & \text{if hours\_until\_due} \le 0 \\ \min\left(\frac{\text{estimated\_hours}}{\text{available\_study\_hours}}, 1.0\right) & \text{otherwise} \end{cases}$$
   $$\text{impact} = \min\left(\frac{\text{grade\_weight}}{50.0}, 1.0\right)$$
   $$\text{difficulty\_factor} = \frac{\text{difficulty} - 1}{4.0}$$
   $$\text{score} = 100.0 \times (0.50 \cdot \text{time\_pressure} + 0.35 \cdot \text{impact} + 0.15 \cdot \text{difficulty\_factor})$$
   $$\text{overdue} = \text{hours\_until\_due} < 0$$
   $$\text{urgent} = \text{hours\_until\_due} \le 24.0$$

6. **Sorting Invariants (`sort_tasks`):**
   - Incomplete tasks MUST always be placed before completed tasks.
   - Incomplete deadline sort: `(due_at ASC, id ASC)`.
   - Incomplete smart sort: `(score DESC, due_at ASC, id ASC)`.
   - Completed tasks sort: `(completed_at DESC, id ASC)` with `priority = None`.

### Benchmark Targets & Edge Cases You Must Cover in `tests/test_scoring.py`
Benchmark baseline: `now = 2026-11-17T12:00:00Z`, `daily_study_hours = 3.0`.
- [ ] **Benchmark Task A (Quiz):** Due in 24h, weight 5%, 1h effort, difficulty 1. Must score **20.2**, with `urgent=True`, `overdue=False`.
- [ ] **Benchmark Task B (Project):** Due in 14 days, weight 30%, 20h effort, difficulty 4. Must score **56.1**, with `time_pressure ≈ 0.476`, `impact = 0.600`, `difficulty_factor = 0.750`, `urgent=False`, `overdue=False`.
- [ ] **Benchmark Task C (Overdue HW):** Due 2h ago, weight 10%, 2h effort, difficulty 3. Must score **64.5**, with `time_pressure = 1.0`, `overdue=True`, `urgent=True`.
- [ ] **Urgent Cutoff Boundary:** Exactly 24.0 hours remaining must evaluate to `urgent = True`. Exactly 24 hours + 1 second remaining must evaluate to `urgent = False`.
- [ ] **Impact Cap:** Grade weight of 80% must cap `impact` at 1.0. Grade weight of 0% must produce `impact = 0.0`.
- [ ] **Difficulty Range:** Difficulty 1 must yield `difficulty_factor = 0.0`. Difficulty 5 must yield `difficulty_factor = 1.0`.
- [ ] **Bandwidth Sensitivity:** Lowering `daily_study_hours` from 3.0 to 1.0 must strictly increase `time_pressure` for future tasks.
- [ ] **Completed Task Handling:** Any task with `completed = True` passed to `compute_priority` must return `None`.
- [ ] **Tie-Breaking:** If two incomplete tasks produce identical smart scores, tie-break by `due_at ASC`, then by `id ASC`.
- [ ] **Completed Sinking:** In both deadline and smart sorting, completed tasks must sink to the bottom and be ordered by `completed_at DESC`.

### Step-by-Step Execution Plan
1. Create `tests/test_scoring.py` defining mock tasks and test cases for all benchmark figures and edge cases.
2. Run `uv run pytest tests/test_scoring.py -v` and confirm failure.
3. Implement `app/tasks/scoring.py` with pure functions and module-level constants.
4. Run `uv run pytest tests/test_scoring.py -v` and ensure all assertions pass.

---

## Day 1 Definition of Done

Day 1 is complete ONLY when:
1. `uv run pytest -v` runs both test suites and passes 100% with zero warnings or errors.
2. No database or web framework code is imported inside `app/tasks/scoring.py`.
3. No secrets or unnecessary cache files exist unstaged.
4. All work is reviewed and ready for you to commit on your feature branch:
   ```bash
   git status
   # Ensure clean state, then commit per AGENTS.md:
   # git add app/ tests/ pyproject.toml uv.lock .python-version .env.example
   # git commit -m "feat(core): scaffold project, settings, UTC type, and pure scoring engine"
   ```
