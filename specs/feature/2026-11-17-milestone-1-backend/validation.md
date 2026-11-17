# Milestone 1 Backend — Validation

**Feature folder:** `specs/feature/2026-11-17-milestone-1-backend/`  
**Milestone:** M1 (see [`specs/roadmap.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/specs/roadmap.md))  
**Governed by:** [`specs/constitution.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/specs/constitution.md) and [`specs/tech-stack.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/specs/tech-stack.md)

---

## 1. Automated Test Matrix (`uv run pytest`)

| Test Suite File | Coverage Target | Key Test Cases & Invariants |
|---|---|---|
| `tests/test_core.py` | Settings & UTC Types | `SECRET_KEY` required; default expiry is 7 days; `UTCDateTime` converts offset datetimes to naive UTC on write, rejects naive datetimes on write, and re-attaches aware UTC on read. |
| `tests/test_scoring.py` | Priority Engine (Pure) | Exact scores for reference tasks A=20.2, B=56.1, C=64.5; boundary test at 24h urgent cutoff (24h vs 24h+1s); impact cap at 50% weight; difficulty factor 0.0 to 1.0; completed tasks return `None`; deadline sort order; smart sort order; completed tasks sorted to bottom by `completed_at desc`. |
| `tests/test_auth.py` | Authentication & Tokens | Register 201; duplicate username (409); duplicate email (409); case-insensitive duplicate email; short password (422); login with email; login with username; invalid credentials (401); protected routes return 401 without token; malformed token (401); expired token (401); token of deleted user (401); credentials never returned. |
| `tests/test_users.py` | User Profiles | `GET /users/me` profile; `PATCH /users/me` study hours within 0.5–16.0 (200), outside bounds (422); `DELETE /users/me` removes user and cascades all owned records. |
| `tests/test_courses.py` | Course Management | `POST /courses` creates course (201); valid hex color `#3B82F6` succeeds; invalid color `"blue"` or `"#FFF"` fails (422); `GET /courses` returns user's courses; `GET /courses/{id}` returns course; `PATCH /courses/{id}` partially updates; `DELETE /courses/{id}` returns 204. |
| `tests/test_tasks_crud.py` | Task CRUD & Validation | Create task with/without course (201); setting foreign `course_id` returns 404; deleting course leaves task with `course_id = null`; decimal float precision (12.3); UTC offset parsing (+08:00 returned as Z); field validation bounds (difficulty 1–5, hours > 0); toggling `completed=true` sets `completed_at` and clears priority; toggling `completed=false` clears `completed_at`; re-completing already-done task retains original `completed_at`. |
| `tests/test_tasks_queue.py` | Sorting & Filtering | Default sort is deadline (`due_at asc`); `sort=smart` orders by score descending; invalid sort mode returns 422; filter by `course_id`; filter by `category`; filter by `completed`; pagination offset & limit with `total` count; `GET /tasks/top` defaults to top 3 smart incomplete tasks. |
| `tests/test_isolation.py` | Cross-Tenant Security & IDOR | User B accessing User A's course returns masked 404; User B accessing User A's task returns masked 404; User B creating task with User A's `course_id` returns 404; User B's `/courses` and `/tasks` listings never contain User A's data. |
| `tests/test_migrations.py` | Database Evolution | `alembic upgrade head` creates `users`, `courses`, `tasks`, and foreign keys; `ON DELETE CASCADE` on `users.id`; `ON DELETE SET NULL` on `courses.id`; `alembic downgrade base` and re-upgrade succeeds cleanly. |

---

## 2. Reference Priority Fixtures

Frozen benchmark timestamp: `now = 2026-11-17T12:00:00Z`  
Student preference: `daily_study_hours = 3.0`

| Task Code | Category | `due_at` | Grade Weight | Estimated Hours | Difficulty | Time Pressure | Grade Impact | Difficulty Factor | Score | Urgency Flags |
|---|---|---|---|---|---|---|---|---|---|---|
| **A (Quiz)** | `quiz` | `now + 24h` | 5.0% | 1.0 h | 1 (Easy) | 0.333 | 0.100 | 0.000 | **20.2** | `urgent: true`, `overdue: false` |
| **B (Project)** | `project` | `now + 14d` | 30.0% | 20.0 h | 4 (Hard) | 0.476 | 0.600 | 0.750 | **56.1** | `urgent: false`, `overdue: false` |
| **C (Overdue HW)** | `homework` | `now - 2h` | 10.0% | 2.0 h | 3 (Med) | 1.000 | 0.200 | 0.500 | **64.5** | `urgent: true`, `overdue: true` |

### Benchmark Sort Order Expectations
- **Deadline Sort (`SortMode.deadline`):** Task C (overdue) → Task A (+24h) → Task B (+14d).
- **Smart Sort (`SortMode.smart`):** Task C (64.5) → Task B (56.1) → Task A (20.2).

---

## 3. Mandatory Constitution Compliance Matrix

| Rule ID | Invariant Description | How M1 Enforces It | Verified By |
|---|---|---|---|
| **Axiom 1** | Explainable priority | Incomplete tasks always return `PriorityResult` with every individual component breakdown. | `tests/test_scoring.py`, `tests/test_tasks_crud.py` |
| **Axiom 2 / S-3** | Privacy by default & 404 masking | Unauthorized access to foreign tasks or courses returns `404 Not Found` identical to nonexistent records. | `tests/test_isolation.py` |
| **Axiom 3** | Pure unit-tested scoring | `tasks/scoring.py` is a pure library with zero DB/framework dependencies, evaluated against reference fixtures. | `tests/test_scoring.py` |
| **S-1** | Single auth gateway | All protected endpoints resolve user identity through `auth/dependencies.py:get_current_user`. | `tests/test_auth.py` |
| **S-2** | Ownership in SQL query | Service queries filter `owner_id == user.id` in SQL statements before data retrieval. | `tests/test_isolation.py` |
| **S-4** | Credential security | Passwords hashed with Argon2; JWT signed with environment `SECRET_KEY`; secrets excluded from git. | `tests/test_auth.py`, code audit |
| **S-5** | Least-privilege DB user | App connects using dedicated `taskqueue` MySQL user; no `root` credentials in application runtime. | Manual setup runbook |
| **D-1** | MySQL 8 everywhere | PyMySQL with InnoDB and `utf8mb4`; tests execute against `taskqueue_test`. | `tests/conftest.py` guard |
| **D-2** | Migrations only | Application runtime never calls `create_all`; test runner validates Alembic migrations. | `tests/test_migrations.py` |
| **D-3** | Cascading foreign keys | User deletion cascades courses and tasks; course deletion sets task `course_id = null`. | `tests/test_users.py`, `tests/test_tasks_crud.py` |
| **D-4** | UTC discipline | All timestamps stored as UTC `DATETIME(6)`; naive datetimes rejected at edge (`AwareDatetime`). | `tests/test_core.py`, `tests/test_tasks_crud.py` |
| **D-5** | Scores not persisted | No priority score columns in MySQL schema; scores computed on read. | `tests/test_migrations.py`, schema audit |
| **D-6** | Edge validation | Pydantic v2 schemas enforce all string lengths, regex patterns, and numeric ranges. | `tests/test_courses.py`, `tests/test_tasks_crud.py` |
| **M1 Scope** | Out-of-scope discipline | Zero Docker, Redis, Celery, ML models, email sending, or frontend assets in Milestone 1. | Codebase inspection |

---

## 4. Manual QA & Exploratory Testing Runbook

Execute locally against the running development server (`uv run fastapi dev app/main.py`):

1. **Database Preparation:**
   ```bash
   uv run alembic upgrade head
   ```
2. **Access Interactive Docs:** Open browser to `http://127.0.0.1:8000/docs`.
3. **Register Student:** Call `POST /auth/register` with `{"username": "teststudent", "email": "student@school.edu", "password": "password123"}`. Verify HTTP 201.
4. **Authorize:** Click the green **Authorize** button in Swagger UI. Enter `student@school.edu` (or `teststudent`) and `password123`. Verify token accepted.
5. **Create Course:** Call `POST /courses` with `{"name": "Computer Science I", "code": "CS101", "color": "#3B82F6"}`. Note the returned `course.id`.
6. **Create Tasks A, B, C:**
   - Create Task A (Quiz, due in 24 hours, weight 5%, 1 hour, difficulty 1, linked to `course_id`).
   - Create Task B (Project, due in 14 days, weight 30%, 20 hours, difficulty 4, linked to `course_id`).
   - Create Task C (Homework, due 2 hours ago, weight 10%, 2 hours, difficulty 3, no course).
7. **Verify Queue Ordering:**
   - Call `GET /tasks?sort=deadline`: Verify order is C, A, B.
   - Call `GET /tasks?sort=smart`: Verify order is C (score ~64.5), B (score ~56.1), A (score ~20.2).
8. **Verify Course Filtering:** Call `GET /tasks?course_id=1`. Verify only Tasks A and B appear.
9. **Test Course Deletion Safety:** Call `DELETE /courses/1`. Call `GET /tasks/{A's id}`: verify Task A still exists and `course` is `null`.
10. **Test Isolation (IDOR):** In an incognito window, register a second user (`hacker`). Attempt `GET /tasks/{A's id}` using the second user's token. Verify response is `404 Not Found`.
11. **Test Account Deletion:** Call `DELETE /users/me`. Verify HTTP 204. Call `GET /users/me` with old token: verify `401 Unauthorized`.
