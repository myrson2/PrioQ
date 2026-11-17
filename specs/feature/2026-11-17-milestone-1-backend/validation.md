# Milestone 1 Backend — Validation

**Feature folder:** `specs/feature/2026-11-17-milestone-1-backend/` · **Milestone:** M1 (see `specs/roadmap.md`) · **Governed by:** `specs/constitution.md`

## 1. Automated Test Matrix (`uv run pytest`)
| Area | File | Key cases |
|---|---|---|
| Scoring (unit, no DB) | `test_scoring.py` | A = 20.2, B = 56.1, C = 64.5; overdue → pressure 1.0, `overdue` & `urgent`; exactly 24h → urgent, 24h + 1s → not; impact caps at 1.0 for weight ≥50; weight 0 → impact 0; difficulty 1→0, 5→1; huge estimate caps pressure at 1.0; completed → `None`; lower `daily_study_hours` raises pressure |
| Ordering (unit) | `test_scoring.py` | deadline order; smart order; tie-break due_at then id; completed after incomplete, by completed_at desc |
| Auth | `test_auth.py` | register 201; duplicate email in different case 409; password 7 chars 422; login OK; wrong password 401; unknown email 401; no token / garbage token / expired token / deleted-user token → 401 on a protected route; no password or hash in any response |
| Users | `test_users.py` | GET me; PATCH study hours 0.5 and 16 OK, 0.4 and 16.1 → 422; DELETE me → 204 and their task rows gone from MySQL |
| Task CRUD | `test_tasks_crud.py` | create 201 with priority block; field edges (OK at edge, 422 just outside); naive `due_at` 422; `+08:00` input comes back as UTC `Z`; whitespace-only title 422; decimal round-trip (`grade_weight` 12.3 comes back exactly 12.3); GET by id; PATCH partial keeps other fields; `title: null` 422; `description: null` OK; completed true sets `completed_at`, false clears it; DELETE 204 then 404 |
| Queue | `test_tasks_queue.py` | default sort = deadline; `sort=smart`; `sort=bogus` 422; category filter; completed filter; limit/offset + `total`; `limit=201` 422; `/tasks/top` default 3, smart, excludes completed; `n=11` 422 |
| Isolation (security) | `test_isolation.py` | user B: GET / PATCH / DELETE A's task → 404, same body as a missing id; B's `/tasks` and `/tasks/top` never include A's tasks |
| Migrations | `test_migrations.py` | after `upgrade head`, `users`, `tasks`, `alembic_version` exist; FK on `tasks.owner_id` has `ON DELETE CASCADE`; `downgrade base` then `upgrade head` succeeds |

## 2. Reference Fixtures (frozen `now = 2026-11-17T12:00:00Z`, `daily_study_hours = 3`)
| Task | due_at | weight | hours | difficulty | pressure | impact | diff | score | flags |
|---|---|---|---|---|---|---|---|---|---|
| A quiz | now + 24h | 5 | 1 | 1 | 0.333 | 0.1 | 0.0 | **20.2** | urgent |
| B project | now + 14d | 30 | 20 | 4 | 0.476 | 0.6 | 0.75 | **56.1** | — |
| C homework | now − 2h | 10 | 2 | 3 | 1.0 | 0.2 | 0.5 | **64.5** | urgent, overdue |

## 3. Constitution Compliance Matrix
| ID | Invariant | How M1 enforces it | Verified by |
|---|---|---|---|
| Axiom 1 | Explainable priority | `priority` block with every factor on every incomplete task | test_tasks_crud, test_scoring |
| Axiom 2 / S-3 | Privacy, 404 masking | same 404 + body for missing and not-yours | test_isolation |
| Axiom 3 | Test-first, pure scoring | `scoring.py` imports no DB/FastAPI; `now` injected | test_scoring + review |
| S-1 | Single gateway | all protected routes depend on `get_current_user` only | test_auth (401 on each route) + review |
| S-2 | Ownership in the query | service queries filter `owner_id` in SQL | test_isolation + review |
| S-4 | Credentials | Argon2; `SECRET_KEY` required; `.env` gitignored | test_auth + review |
| S-5 | Least-privilege DB user | dedicated `taskqueue` MySQL user | setup runbook |
| D-1 | MySQL everywhere | PyMySQL URLs only; tests on `taskqueue_test` | conftest guard |
| D-2 | Migrations only | app never calls `create_all`; tests migrate with Alembic | test_migrations + review |
| D-3 | Cascading ownership | `ON DELETE CASCADE` + ORM cascade | test_users, test_migrations |
| D-4 | UTC everywhere | `UTCDateTime`; `AwareDatetime` input | test_tasks_crud |
| D-5 | Scores not stored | no score column; computed per request | schema review |
| D-6 | Validate at the edge | Pydantic bounds + DB constraints | test_tasks_crud, test_users |
| M1 scope | Forbidden items absent | no Docker, Redis, ML, CORS, email, deploy config | review |

## 4. Manual QA Runbook
1. One-time: run the MySQL setup SQL (implementation.md §1); copy `.env.example` to `.env` and fill in `SECRET_KEY`, `DATABASE_URL`, `TEST_DATABASE_URL`.
2. `uv sync`, then `uv run alembic upgrade head`, then `uv run fastapi dev app/main.py`.
3. In `/docs`: register `ana@test.com`, click **Authorize**, log in.
4. Create tasks shaped like A, B, C from §2, with due dates relative to now. Check `GET /tasks` → C, A, B and `?sort=smart` → C, B, A.
5. `PATCH /users/me` with `daily_study_hours: 1` → B's score rises.
6. Mark A completed → it moves to the bottom with `priority: null`.
7. Register a second user, `GET /tasks/{A's id}` → 404.
8. `DELETE /users/me` as the second user → 204; logging in again → 401.
9. `uv run pytest` → all green.
