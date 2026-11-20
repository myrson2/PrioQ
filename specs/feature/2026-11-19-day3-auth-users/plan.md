# Day 3 Execution Plan — Authentication & Profile Service (~2.5h)

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`. Implement task-by-task; track with `- [ ]` checkboxes.

**Goal:** Deliver the M1 identity layer: Argon2/JWT helpers, single auth gateway, registration, flexible login, and `/users/me`, with full failure-case coverage.  
**Architecture:** Feature modules (`app/auth/`, `app/users/`) plus `app/core/security.py` and `app/main.py`; they consume the Day 2 models from `app/models/`. Routers stay thin; all identity resolution flows through `get_current_user`.  
**Tech Stack:** Python 3.12 (uv), FastAPI, Pydantic v2, SQLAlchemy 2.0 sync, PyJWT, pwdlib[argon2], pytest, httpx, MySQL 8 / `taskqueue_test`.  
**Spec:** `specs/feature/2026-11-19-day3-auth-users/` (`specification.md`, `implementation.md`, `validation.md`).

---

### Schedule
| Day | Focus Area | Tasks Included | Est. Time | Deliverable |
|---|---|---|---|---|
| Day 1 | Foundation & Priority Math | Task 1–2 | ~3.0h | Config, UTC type, pure scoring |
| Day 2 | Database Models & Migrations | Task 3 | ~2.5h | MySQL schema + guarded harness |
| **Day 3** | **Authentication & Users** | **Task 4** | **~2.5h** | **Working register/login/profile lifecycle** |
| Day 4 | Academic Domain CRUD | Task 5–6 | ~3.5h | Course + task routers |
| Day 5 | Queue Engine & Delivery | Task 7–8 | ~3.5h | Queues, isolation suite, context record |

### Global Constraints
- All commands via `uv run`; no bare `python`/`pip`. Sync `def` endpoints only.
- MySQL 8 / InnoDB / utf8mb4 including tests; no SQLite (D-1). No new schema or Alembic revision (D-2).
- `get_current_user` only identity resolver (S-1); no header/token parsing in routes.
- Ownership is implicit via `/users/me`; no cross-user ID routes (S-2, Axiom 2 / S-3).
- Argon2 + HS256; secrets from `.env`; no credential logging (S-4). Dedicated DB user (S-5).
- `UTCDateTime` on read; timezone-aware inputs only (D-4). No score columns (D-5).
- No git commits without explicit owner instruction.

### Prerequisite
Day 2 is complete: `taskqueue` and `taskqueue_test` exist, `uv run alembic upgrade head` has been applied, and `.env` contains `SECRET_KEY`, `DATABASE_URL`, `TEST_DATABASE_URL`. No new migration is needed.

### Review Focus
1. **Flexible login** — login with `alex_dev` or `alex@school.edu` case-insensitively: `test_login_with_username_or_email`.
2. **Stale token** — token from deleted user yields generic `401`: `test_token_of_deleted_user_is_401`.
3. **Duplicate registration** — 409 for both username and email: `test_duplicate_registration_is_409`.
4. **Hash never leaks** — `hashed_password` absent from every response: `test_user_read_never_returns_hash`.
5. **Cascade delete** — account deletion removes courses/tasks: `test_delete_user_cascades_children`.

---

### DAY 3: Authentication & Profile Service (~2.5h)

### Task 4: Security, auth routes, and `/users/me` (~2.5h)

**Files:**
- Create: `app/core/security.py`, `app/users/schemas.py`, `app/users/router.py`, `app/auth/__init__.py`, `app/auth/router.py`, `app/auth/dependencies.py`, `app/main.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_auth.py`, `tests/test_users.py`

**Interfaces:**
- Consumes: `get_settings`, `Base`/`UTCDateTime`/`utcnow`, `User`, `DbSession` (Days 1–2).
- Produces:
  - `security.hash_password`, `verify_password`, `create_access_token`, `decode_access_token`.
  - `UserCreate`, `UserRead`, `UserUpdate`, `Token`.
  - `auth.dependencies.get_current_user -> User`, `oauth2_scheme`.
  - Routes: `POST /auth/register`, `POST /auth/login`, `GET /users/me`, `PATCH /users/me`, `DELETE /users/me`.
  - `app.main.app` FastAPI entrypoint.
  - `tests/conftest.py` fixtures `client`, `make_user`, `auth_headers`.

- [ ] **Step 1: Write failing tests** in `tests/test_auth.py` and `tests/test_users.py` covering US-1…US-6 and all five Review Focus cases.
- [ ] **Step 2: Observe failure**  
  Run: `uv run pytest tests/test_auth.py tests/test_users.py -v`  
  Expected: FAIL (modules do not exist).
- [ ] **Step 3: Implement `app/core/security.py` and `app/users/schemas.py`**
- [ ] **Step 4: Implement `app/auth/dependencies.py` and `app/auth/router.py`**
- [ ] **Step 5: Implement `app/users/router.py` and `app/main.py`**
- [ ] **Step 6: Extend `tests/conftest.py` with client/user/token fixtures**
- [ ] **Step 7: Verify pass**  
  Run: `uv run pytest tests/test_auth.py tests/test_users.py -v`  
  Expected: PASS.
- [ ] **Step 8: Regression gate**  
  Run: `uv run pytest -v`  
  Expected: all Day 1/2/3 tests pass.

**Definition of Done:** identity resolved only by `get_current_user`; no hash in responses; no new migration; full suite green; clean working tree; owner commits on a feature branch.
