# Milestone 1 Backend — Specification

**Feature folder:** `specs/feature/2026-11-17-milestone-1-backend/` · **Milestone:** M1 (see `specs/roadmap.md`) · **Governed by:** `specs/constitution.md`

## 1. Context & Motivation
See `specs/mission.md` and `specs/roadmap.md` (Milestone 1). Deadline-only sorting hides heavy, high-impact work until it's an emergency. Milestone 1 delivers the backend only: a FastAPI + SQLAlchemy + MySQL REST API with user accounts, task CRUD, and two queue orderings — **deadline** (nearest first) and **smart** (a rule-based, explainable 0–100 score). It must be ready for usability testing after Milestone 2. Milestone 3 may change the schema and add an ML model behind the same scoring interface.

## 2. Goals / Non-goals / Anti-goals
- **Goals:** accounts with per-user isolation; full task CRUD; deadline and smart sorting with a score breakdown; Alembic migrations on MySQL; automated pytest suite plus manual `/docs` checks.
- **Non-goals (deferred):** everything in the constitution's M1 out-of-scope list (Docker, Redis, ML, frontend/CORS, email, deployment), plus refresh tokens, progress / hours-spent tracking, courses/subjects, title search, due-date range filters.
- **Anti-goals:** a student seeing or inferring another student's tasks; a score nobody can explain; urgent tasks silently buried.

## 3. User Stories
- **US-1 Register:** GIVEN a new student WHEN they submit email + password THEN an account is created with `daily_study_hours = 3.0`.
- **US-2 Login:** GIVEN a registered student WHEN they log in with correct credentials THEN they get a bearer token valid for 7 days.
- **US-3 Create task:** GIVEN a logged-in student WHEN they submit a valid task THEN it is saved under their account and returned with its priority breakdown.
- **US-4 Deadline queue:** GIVEN several tasks WHEN the student calls `GET /tasks` THEN incomplete tasks come nearest-deadline first, completed tasks at the bottom.
- **US-5 Smart queue:** GIVEN several tasks WHEN the student calls `GET /tasks?sort=smart` THEN incomplete tasks are ordered by score, highest first, each with its breakdown and an `urgent` flag.
- **US-6 Top tasks:** GIVEN several tasks WHEN the student calls `GET /tasks/top?n=3` THEN they get their top 3 incomplete tasks (smart order by default).
- **US-7 Complete task:** GIVEN a task WHEN the student sets `completed=true` THEN `completed_at` is recorded and the task drops to the bottom; setting it back to `false` clears `completed_at`.
- **US-8 Isolation:** GIVEN student B WHEN B requests, edits or deletes student A's task THEN B gets `404 Not Found`.
- **US-9 Study hours:** GIVEN a student WHEN they change `daily_study_hours` THEN smart scores reflect it on the next fetch.
- **US-10 Delete account:** GIVEN a student WHEN they call `DELETE /users/me` THEN their account and all their tasks are removed.

## 4. Functional Requirements
- **FR-1** `POST /auth/register` creates a user; email is unique regardless of case (stored lowercased); duplicate → `409`.
- **FR-2** `POST /auth/login` uses the OAuth2 password form (`username` = email, `password`); returns `{access_token, token_type: "bearer"}`.
- **FR-3** Every `/tasks*` and `/users/me*` route requires a valid bearer token via `get_current_user` (constitution S-1).
- **FR-4** `GET / PATCH / DELETE /users/me`: read, update (`daily_study_hours` only), delete the account (cascade-deleting tasks).
- **FR-5** Task fields: `title`, optional `description`, `category ∈ {quiz, homework, project, exam, other}`, `due_at` (timezone-aware ISO 8601), `grade_weight` (0–100), `estimated_hours` (>0, ≤500), `difficulty` (1–5), `completed` (bool).
- **FR-6** Task routes: `POST /tasks`, `GET /tasks`, `GET /tasks/top`, `GET /tasks/{id}`, `PATCH /tasks/{id}` (partial), `DELETE /tasks/{id}`.
- **FR-7** `GET /tasks` supports `sort=deadline|smart` (default `deadline`), `category`, `completed`, `limit` (default 50, max 200), `offset` (≥0).
- **FR-8** Every task response includes a computed `priority` block (score, breakdown, flags), or `null` for completed tasks. Scores are never stored (D-5).
- **FR-9** Smart score formula and ordering exactly as in `implementation.md` §5.
- **FR-10** Past due dates are allowed on create/update; such tasks are `overdue` and `urgent`.

## 5. Non-Functional Requirements
- **Security:** constitution S-1 to S-5.
- **Data:** constitution D-1 to D-6; all datetimes UTC.
- **Performance:** personal scale (hundreds to low thousands of tasks per user); sorting in Python is acceptable.
- **Errors:** FastAPI's `{"detail": ...}` shape; validation errors are `422`.

## 6. Acceptance Criteria
- [ ] Register → login → Authorize in `/docs` → full task CRUD works manually.
- [ ] Reference tasks A, B, C (validation.md §2) score **20.2**, **56.1**, **64.5**; deadline order C, A, B; smart order C, B, A.
- [ ] Completed tasks always come after incomplete ones and have `priority: null`.
- [ ] User B gets `404` for every operation on user A's task.
- [ ] `DELETE /users/me` removes the user's tasks from MySQL.
- [ ] `uv run alembic upgrade head` builds the schema on an empty MySQL DB; `uv run pytest` passes.
