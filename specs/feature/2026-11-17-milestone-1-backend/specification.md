# Milestone 1 Backend — Specification

**Feature folder:** `specs/feature/2026-11-17-milestone-1-backend/`  
**Milestone:** M1 (see [`specs/roadmap.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/specs/roadmap.md))  
**Governed by:** [`specs/constitution.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/specs/constitution.md) and [`specs/tech-stack.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/specs/tech-stack.md)

---

## 1. Context & Motivation
Students constantly struggle with competing academic priorities—quizzes, homework assignments, exams, and heavy term projects—each possessing different due dates, grade weights, and time commitments. Traditional to-do apps sort strictly by calendar deadlines. This causes severe procrastination: large 20-hour projects worth 30% of a final grade stay out of sight until days before the deadline, while students deplete their energy on trivial 1-hour quizzes.

Milestone 1 delivers the foundational backend REST API on MySQL 8. It provides multi-tenant student authentication, academic course management (with visual hex color badges for M2), task CRUD with optional course linkages, and dual queue sorting:
1. **Deadline Queue (`?sort=deadline`):** Chronological, nearest deadline first.
2. **Smart Queue (`?sort=smart`):** Dynamic 0–100 mathematical priority engine balancing urgency against available study bandwidth, grade impact, and task difficulty, complete with an explainable factor breakdown and an urgent/overdue safety flag.

This backend serves as the single source of truth for the Milestone 2 web frontend and provides the baseline priority metric for the Milestone 3 Machine Learning model.

---

## 2. Approaches Considered & Decision
- **Approach 1 (Lean 2-table schema):** Only `users` and `tasks`. Rejected because assignment weights and categories naturally belong to academic courses, and the UI lacks course metadata for visual badges.
- **Approach 2 (Academic 3-table schema — SELECTED):** `users`, `courses`, and `tasks`. Tasks feature an optional `course_id`. Gives natural structure to a student's semester while still accommodating general non-course academic to-dos (e.g., "Submit financial aid form"). Deleting a course cleanly disassociates tasks (`ON DELETE SET NULL`) without destroying the student's task history.
- **Approach 3 (Enterprise 5-table schema):** Separate `categories`, `user_preferences`, and `task_audit_logs`. Rejected because audit tables create write spam on dynamic scoring, and database-persisted priority scores cause immediate data staleness bugs, violating Constitution Rule **D-5**.

---

## 3. Goals, Non-goals, and Anti-goals

### Goals
- Secure student account registration and login via JWT bearer tokens (7-day validity).
- User profile management including configurable `daily_study_hours` (default 3.0, range 0.5–16.0).
- Course CRUD (`/courses`) with unique names, subject codes, and hex color codes.
- Task CRUD (`/tasks`) with optional course association, category enum, difficulty, effort, and grade weight.
- Dynamic queue ordering (`?sort=deadline` and `?sort=smart`) with complete score transparency.
- Quick-access endpoint (`GET /tasks/top?n=3`) returning the top actionable tasks for today's dashboard.
- Strict multi-tenant data isolation: all resources query by `owner_id == current_user.id`, masking unauthorized cross-tenant requests with `404 Not Found` (Constitution S-2, S-3).
- Automated test coverage across unit scoring, CRUD, auth, and IDOR security on a real MySQL test database.

### Non-goals (Milestone 1 Out-of-Scope)
- Web frontend UI and CORS configuration (deferred to Milestone 2).
- Machine learning models, datasets, and Pandas training loops (deferred to Milestone 3).
- Redis caching layers, Docker containerization, Celery background workers, and email delivery.
- Refresh tokens, password reset flows, and subtask checklist items.

### Anti-goals
- **Never store priority scores in MySQL columns:** Priority is time-dependent (`due_at - now`). Storing it in a database table causes immediate staleness.
- **No data leakage:** A student must never be able to discover or infer another student's courses or tasks.
- **No unexplainable black-box ranking:** Every score returned must expose its constituent mathematical factors.

---

## 4. User Stories

- **US-1 Student Registration:** GIVEN a new student WHEN they register with a username, email, and password THEN their account is created with `daily_study_hours = 3.0` and passwords hashed with Argon2.
- **US-2 Flexible Login:** GIVEN an existing student WHEN they log in using either their username OR email and their password THEN they receive a 7-day bearer token.
- **US-3 Course Setup:** GIVEN an authenticated student WHEN they create courses (e.g., Code `"CS101"`, Name `"Computer Science I"`, Color `"#3B82F6"`) THEN they can view, edit, and delete their own courses.
- **US-4 Task Creation with Course:** GIVEN a student with courses WHEN they create a task linking to `course_id` THEN the task is saved and returned with course metadata and priority score.
- **US-5 General Task Creation:** GIVEN a student WHEN they create a task without specifying a `course_id` THEN the task is created as an unlinked general academic task (`course_id = null`).
- **US-6 Cross-User Protection (IDOR):** GIVEN Student B WHEN B attempts to fetch, edit, delete, or link to Student A's course or task THEN the API returns `404 Not Found`.
- **US-7 Safe Course Deletion:** GIVEN a course with linked tasks WHEN the student deletes the course THEN the course is deleted but the linked tasks remain intact with `course_id = null`.
- **US-8 Smart Queue Prioritization:** GIVEN several tasks with varying weights and deadlines WHEN the student calls `GET /tasks?sort=smart` THEN tasks are sorted by score desc, bringing urgent and high-impact work to the top with an explainable breakdown.
- **US-9 Completed Task Handling:** GIVEN an incomplete task WHEN marked `completed = true` THEN `completed_at` is timestamped, priority becomes `null`, and the task sinks to the bottom of the queue.
- **US-10 Account Deletion:** GIVEN an authenticated student WHEN they call `DELETE /users/me` THEN their account, courses, and tasks are permanently cascade-deleted.

---

## 5. Functional Requirements

- **FR-1 Authentication:** `POST /auth/register` creates a user. `username` (3–50 chars, alphanumeric + underscores) and `email` must be unique (case-insensitive). Duplicate registrations return `409 Conflict`.
- **FR-2 Login:** `POST /auth/login` implements OAuth2 Password request (`username` field accepts email or username, and `password`). Valid credentials return `{access_token: str, token_type: "bearer"}`.
- **FR-3 Single Auth Gateway:** All protected endpoints require a valid bearer JWT parsed strictly via FastAPI dependency `get_current_user` (Constitution S-1).
- **FR-4 User Management:**
  - `GET /users/me`: Returns the current user's profile.
  - `PATCH /users/me`: Updates `daily_study_hours` (0.5 to 16.0).
  - `DELETE /users/me`: Permanently deletes the account and cascades all owned records (Constitution D-3).
- **FR-5 Course Management (`/courses`):**
  - `POST /courses`: Creates course with `name` (1–100 chars), `code` (1–20 chars), and `color` (7-char hex string matching `^#[0-9A-Fa-f]{6}$`, default `"#3B82F6"`).
  - `GET /courses`: Returns a list of all courses owned by the authenticated user.
  - `GET /courses/{id}`: Returns the specific course (or 404).
  - `PATCH /courses/{id}`: Partially updates `name`, `code`, or `color`.
  - `DELETE /courses/{id}`: Deletes course and sets linked tasks' `course_id = null`.
- **FR-6 Task Management (`/tasks`):**
  - `POST /tasks`: Creates task with fields `title` (1–200 chars), optional `description` (≤2000 chars), optional `course_id` (must belong to user, else 404), `category ∈ {quiz, homework, project, exam, other}`, `due_at` (UTC timezone-aware), `grade_weight` (0.0–100.0), `estimated_hours` (0.1–500.0), `difficulty` (1–5), and `completed` (bool, default false).
  - `GET /tasks`: Lists tasks with pagination (`limit`, `offset`) and filters (`sort`, `course_id`, `category`, `completed`).
  - `GET /tasks/top`: Returns top `n` (1–10, default 3) incomplete tasks sorted by `smart` order.
  - `GET /tasks/{id}`: Fetches specific task.
  - `PATCH /tasks/{id}`: Partially updates task fields.
  - `DELETE /tasks/{id}`: Permanently deletes task.
- **FR-7 Dynamic Scoring:** Every incomplete task response includes a `priority` object containing `score` (0–100), `time_pressure`, `impact`, `difficulty_factor`, `hours_until_due`, `urgent`, and `overdue`. Completed tasks return `priority: null`.

---

## 6. Non-Functional Requirements

- **Security & Privacy:** Passwords hashed with Argon2 via `pwdlib`. JWT signed with `SECRET_KEY` from `.env`. Zero credential leakage. IDOR masking via `404 Not Found`.
- **Data Integrity:** MySQL 8 InnoDB with `utf8mb4`. Foreign keys enforced at database level with `ON DELETE CASCADE` (users) and `ON DELETE SET NULL` (courses). All floating numbers stored as `DOUBLE`.
- **Time Discipline:** All datetimes stored and manipulated in UTC. Rejection of naive timestamps without timezone offsets (`422 Unprocessable Entity`).
- **Reliability & Performance:** Pure priority sorting performed in memory for user-scoped task queues. Connection pooling with `pool_pre_ping=True`.

---

## 7. Acceptance Criteria Checklist

- [ ] `POST /auth/register` creates users; duplicate email or username returns `409 Conflict`.
- [ ] `POST /auth/login` accepts either username or email and returns valid JWT.
- [ ] User can perform full CRUD on `/courses`. Hex color format is strictly validated.
- [ ] User can perform full CRUD on `/tasks`, optionally attaching a course.
- [ ] Attaching another user's `course_id` to a task returns `404 Not Found`.
- [ ] Deleting a course sets `course_id = null` on linked tasks; tasks are not deleted.
- [ ] Deleting an account (`DELETE /users/me`) deletes all associated courses and tasks in MySQL.
- [ ] Incomplete tasks return computed `priority`; completed tasks return `priority = null` and sort at the bottom.
- [ ] `GET /tasks?sort=smart` produces exact reference scores (A=20.2, B=56.1, C=64.5).
- [ ] `GET /tasks?course_id={id}` successfully filters tasks by course.
- [ ] `uv run alembic upgrade head` creates all 3 tables with appropriate constraints.
- [ ] `uv run pytest` runs against MySQL test DB and passes 100%.
