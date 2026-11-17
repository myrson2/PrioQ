# Milestone 1 Backend — Validation

**Feature folder:** `specs/feature/2026-11-17-milestone-1-backend/` · **Milestone:** M1 (see `specs/roadmap.md`) · **Governed by:** `specs/constitution.md`

## 1. Automated Test Matrix (`uv run pytest`)
| Area | File | Key Cases |
|---|---|---|
| Scoring (pure unit) | `test_scoring.py` | Reference scores A=20.2, B=56.1, C=64.5; boundary conditions; impact cap; difficulty mapping; completed is None. |
| Auth & Users | `test_auth.py`, `test_users.py` | Register duplicate username/email (409); short password; login with email OR username; 7-day token; me CRUD; account delete cascade. |
| Courses | `test_courses.py` | Course CRUD; hex color format validation (`#3B82F6` ok, `red` 422); course listing returns only user's own courses. |
| Task CRUD | `test_tasks_crud.py` | Task CRUD with/without `course_id`; setting `course_id` of other user returns 404; deleting course sets `course_id=None` on task; numeric double precision (12.3); UTC offset parsing. |
| Task Queue | `test_tasks_queue.py` | Deadline vs smart sort; filtering by `course_id`; filtering by `category` and `completed`; pagination total/offset; top tasks. |
| Isolation & IDOR | `test_isolation.py` | User B accessing User A's task or course returns identical 404; B cannot attach task to A's course (404); user listing never leaks cross-tenant records. |
| Migrations | `test_migrations.py` | Alembic `upgrade head` against clean MySQL test DB builds `users`, `courses`, `tasks`, foreign keys, cascade rules, and check constraints; `downgrade base` succeeds. |

## 2. Constitution Compliance Matrix
- **Axiom 1 (Explainable Priority):** Tested in `test_tasks_crud.py` and `test_scoring.py`.
- **Axiom 2 / S-3 (Privacy / 404 Masking):** Verified across tasks AND courses in `test_isolation.py`.
- **S-1 (Single Auth Gateway):** Every endpoint protected by `get_current_user` in `auth/dependencies.py`.
- **S-2 (Ownership in SQL Query):** Verified in all service queries for users, courses, and tasks.
- **D-1 (MySQL 8 / InnoDB / utf8mb4):** Verified against `taskqueue_test` via `conftest.py`.
- **D-3 (Cascading Deletes):** User delete cascades courses and tasks; Course delete sets `task.course_id = NULL`.
- **D-5 (Scores Not Persisted):** No score columns in database schema.
