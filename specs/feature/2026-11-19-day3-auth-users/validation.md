# Day 3 — Authentication & Profile Service — Validation

**Feature folder:** `specs/feature/2026-11-19-day3-auth-users/`  
**Milestone:** M1 (see [specs/roadmap.md](../../roadmap.md))  
**Governed by:** [specs/constitution.md](../../constitution.md) and [specs/tech-stack.md](../../tech-stack.md)

---

## 1. Automated Test Matrix (`uv run pytest`)
| Test file | Coverage target | Key cases / invariants |
|---|---|---|
| `tests/test_auth.py` | FR-1, FR-2, FR-3, FR-4 | Hash is not plaintext; register 201/409; flexible case-insensitive login 200/401; token decode; invalid/expired token 401. |
| `tests/test_users.py` | FR-4, FR-5, FR-6, US-3…US-6 | GET/PATCH/DELETE `/users/me`; hash never returned; bounds 0.5–16.0; cascade delete; stale token 401. |
| `tests/conftest.py` | FR-8 | Guarded `_test` DB; `client` overrides `get_db`; `make_user` + `auth_headers`; autouse cleanup. |
| `tests/test_core.py` (regression) | D-1, D-4 | Settings, UTC type. |
| `tests/test_scoring.py` (regression) | Axiom 3 | Scores A=20.2, B=56.1, C=64.5. |
| `tests/test_migrations.py` (regression) | D-2, D-3 | Schema, FKs, upgrade/downgrade cycle. |

## 2. Reference Fixtures
| Fixture | Expected value |
|---|---|
| Fixed `now` | `2026-11-17T12:00:00Z` |
| Test secret | dedicated test-only `SECRET_KEY` (placeholder `<test-secret>` in docs) |
| User payload | `username="alex_dev"`, `email="Alex@School.edu"`, `password="securePassword123"` |
| Normalized email | `alex@school.edu` |
| Token claims | `sub = str(user.id)`, `exp = now + 7 days` |
| Default study hours | `3.0` |
| Wrong credentials detail | `Incorrect username/email or password` |
| Invalid token detail | `Could not validate credentials` |

## 3. Mandatory Constitution Compliance Matrix
| Rule ID | Invariant | How Day 3 enforces it | Verified by |
|---|---|---|---|
| **Axiom 1** | Explainable priority | No scores produced or returned in Day 3; scoring untouched. | `tests/test_scoring.py` regression |
| **Axiom 2 / S-3** | Privacy / 404 masking | No ID-based user routes; identity bound to token, so cross-user access is impossible. | `tests/test_users.py` |
| **Axiom 3** | Pure, test-first scoring | `app/tasks/scoring.py` unchanged; TDD steps in `plan.md`. | `tests/test_scoring.py`, plan checkboxes |
| **S-1** | Single auth gateway | `get_current_user` only resolver; routes use `Depends`. | Code inspection + all protected-route tests |
| **S-2** | Ownership in the query | `/users/me` queries `User.id == token.sub` in SQL; no Python-side ownership checks. | `test_token_of_deleted_user_is_401` |
| **S-4** | Credentials | Argon2, HS256, `SECRET_KEY` from settings; hash never serialized or logged. | `test_user_read_never_returns_hash` |
| **S-5** | Least-privilege DB user | Dedicated `taskqueue` MySQL user in `.env`; tests use `taskqueue_test`. | Existing harness readiness |
| **D-1** | MySQL 8 everywhere | Auth uses the same guarded MySQL engine; no SQLite. | `tests/conftest.py` |
| **D-2** | Migrations only | No new revision; Day 2 schema unchanged. | `tests/test_migrations.py` regression |
| **D-3** | Cascading deletes | `DELETE /users/me` relies on Day 2 `ON DELETE CASCADE` FKs. | `test_delete_user_cascades_children` |
| **D-4** | UTC discipline | `created_at` read via `UTCDateTime`; no naive datetime inputs in Day 3. | `tests/test_core.py` regression |
| **D-5** | Scores not persisted | No score columns or priority fields in Day 3 schemas. | Schema + response inspection |
| **D-6** | Validate at the edge | Pydantic bounds on username/email/password/study hours. | `test_daily_study_hours_bounds`, malformed-input tests |
| **M1 scope** | Out-of-scope discipline | No Docker, Redis, ML, frontend, CORS, email, or course/task routers. | File inventory |

## 4. Manual QA & Exploratory Runbook
1. Run `uv run fastapi dev app/main.py`.
2. Open `/docs`; call `POST /auth/register` with a new username/email/password; confirm `201` and no hash in response.
3. Click **Authorize**, paste the `access_token`; call `GET /users/me` and confirm the profile.
4. Call `POST /auth/login` with the username, then with the email (mixed case); both succeed.
5. Call `PATCH /users/me` with `4.5`, then with `0.4` and confirm `422`.
6. Create a course/task via direct DB or wait for Day 4; call `DELETE /users/me`, confirm `204` and that child rows disappear.
7. Reuse the pre-deletion token on `/users/me`; confirm `401`.
8. Run `uv run pytest -v`; confirm the full suite is green.
