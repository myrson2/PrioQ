# Milestone 1 Backend — Specification

**Feature folder:** `specs/feature/2026-11-17-milestone-1-backend/` · **Milestone:** M1 (see `specs/roadmap.md`) · **Governed by:** `specs/constitution.md`

## 1. Context & Motivation
See `specs/mission.md` and `specs/roadmap.md`. Pure due-date sorting hides heavy, high-impact coursework until it becomes an emergency. Furthermore, academic assignments do not exist in a vacuum; they belong to specific classes (e.g. "CS 101" or "Math 201"). 

Milestone 1 delivers the full backend foundation: a FastAPI + SQLAlchemy (sync) + MySQL 8 REST API supporting student accounts with usernames, course management, task CRUD with optional course association, and dual queue sorting—**deadline** (nearest first) and **smart** (explainable 0–100 score).

## 2. Approaches Considered & Decision
- **Approach 1 (Lean 2-table):** Just `users` and `tasks`. Rejected because assignment weights only have contextual meaning within a course, and M2 needs course color coding.
- **Approach 2 (Academic 3-table — SELECTED):** `users`, `courses`, and `tasks`. Tasks have an optional `course_id`. Gives natural structure to a student's semester with clean color badges, while still supporting general to-dos.
- **Approach 3 (Enterprise 5-table):** Adding `categories`, `user_preferences`, and `task_audit_logs`. Rejected because audit logs add write overhead on read-time scoring, and DB-persisted priority scores cause immediate staleness bugs (violating Constitution D-5).

## 3. Goals, Non-goals, and Anti-goals
- **Goals:** 
  - User accounts with username, email, and Argon2 password hashing.
  - Course CRUD (`/courses`) scoped to the logged-in student.
  - Task CRUD (`/tasks`) with optional course linkage and category enum.
  - Dual queue sorting (`?sort=deadline` and `?sort=smart`) with complete score breakdown.
  - Multi-tenant security with 404 masking (Axiom 2 / S-3).
  - Alembic migrations and automated test suite on MySQL 8.
- **Non-goals (deferred):** Frontend (M2), CORS (M2), ML model (M3), audit logging tables, refresh tokens, email verification, subtask checklists.
- **Anti-goals:** Storing priority scores in the database; allowing cross-user resource snooping; burying urgent deadlines under low-effort tasks.

## 4. User Stories
- **US-1 Register & Profile:** GIVEN a new student WHEN they register with username, email, and password THEN an account is created with `daily_study_hours = 3.0`.
- **US-2 Course Management:** GIVEN a logged-in student WHEN they create courses (e.g., code `"CS101"`, color `"#3B82F6"`) THEN they can list, update, and delete their own courses.
- **US-3 Task Association:** GIVEN a student with courses WHEN they create a task with an optional `course_id` THEN the task links to that course; if no `course_id` is passed, it is created as a general academic task.
- **US-4 Course Deletion Safety:** GIVEN a course with tasks WHEN the course is deleted THEN the tasks are NOT deleted; their `course_id` becomes `null`.
- **US-5 IDOR Protection on Courses:** GIVEN student B WHEN B attempts to assign student A's `course_id` to a task, or access A's course, THEN the API returns `404 Not Found`.
- **US-6 Queue & Filtering:** GIVEN tasks across multiple courses WHEN the student requests `GET /tasks?course_id=1&sort=smart` THEN tasks are filtered to that course and ranked by priority score.
- **US-7 Score Transparency:** GIVEN an incomplete task WHEN fetched via the API THEN a full breakdown of time pressure, grade impact, difficulty factor, hours until due, and urgency flags is returned.

## 5. Functional Requirements
- **FR-1** `POST /auth/register` accepts `username`, `email`, and `password`. Both `username` and `email` are unique (case-insensitive); duplicates return `409 Conflict`.
- **FR-2** `POST /auth/login` uses OAuth2 password flow (`username` field accepts either email or username, and `password`); returns 7-day bearer JWT.
- **FR-3** `GET / PATCH / DELETE /users/me`: read profile, update `daily_study_hours`, or delete user account (cascading all courses and tasks).
- **FR-4** Courses CRUD: `POST /courses`, `GET /courses`, `GET /courses/{id}`, `PATCH /courses/{id}`, `DELETE /courses/{id}`. All strictly scoped to `owner_id == current_user.id`.
- **FR-5** Course fields: `name` (1–100 chars), `code` (1–20 chars, e.g. `"MATH201"`), `color` (7-char hex code, e.g. `"#10B981"`, default `"#3B82F6"`).
- **FR-6** Tasks CRUD: `POST /tasks`, `GET /tasks`, `GET /tasks/top`, `GET /tasks/{id}`, `PATCH /tasks/{id}`, `DELETE /tasks/{id}`.
- **FR-7** Task fields: `title`, optional `description`, optional `course_id`, `category ∈ {quiz, homework, project, exam, other}`, `due_at` (UTC aware), `grade_weight` (0–100), `estimated_hours` (>0, ≤500), `difficulty` (1–5), `completed` (bool).
- **FR-8** Queue query parameters on `GET /tasks`: `sort=deadline|smart` (default `deadline`), `course_id` (int), `category`, `completed` (bool), `limit` (default 50, max 200), `offset` (≥0).
- **FR-9** `GET /tasks/top`: returns top `n` (1–10, default 3) incomplete tasks, defaulting to smart sort.
- **FR-10** Priority score calculated at runtime (0–100) per `implementation.md` §5; `priority` block is `null` for completed tasks.

## 6. Acceptance Criteria
- [ ] User registration with `username` and `email` works; duplicate usernames or emails return 409.
- [ ] User can create, view, edit, and delete courses.
- [ ] Creating a task with someone else's `course_id` returns `404 Not Found`.
- [ ] Deleting a course sets `course_id = null` on linked tasks without deleting the tasks.
- [ ] Deleting a user account cascades and completely removes all their courses and tasks.
- [ ] `GET /tasks?sort=smart` outputs the exact reference scores (A=20.2, B=56.1, C=64.5).
- [ ] `uv run alembic upgrade head` creates all 3 tables with appropriate foreign keys.
- [ ] Full `uv run pytest` suite passes green.
