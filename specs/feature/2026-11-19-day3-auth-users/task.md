# Day 3 Execution Brief: Authentication & Profile Service

**Feature Folder:** `specs/feature/2026-11-19-day3-auth-users/`  
**Assignee:** Developer (AI agent under owner supervision)  
**Role:** Backend engineer — identity and profile layer  
**Time Budget:** 2.5 hours (hard cap < 4h)  
**Governing Documents:** [specification.md](specification.md), [plan.md](plan.md), [implementation.md](implementation.md), [validation.md](validation.md), [constitution.md](../../constitution.md)

### Lead Architect's Note
Day 3 is the trust boundary for every later route. Do not add course/task endpoints here. Do not add a migration. If you find yourself parsing an `Authorization` header outside `get_current_user`, stop — that violates S-1.

### Task 4 — Security, Auth Routes, and `/users/me`

**Objective:** Implement FR-1…FR-8 and US-1…US-6 with failing tests first.

**Architectural Invariants & Constraints:**
- S-1: only `get_current_user` resolves identity.
- S-4: Argon2 hashing, HS256 JWT, secrets from settings, no credential logging.
- D-4: aware UTC timestamps only; D-2: no new Alembic revision; D-5: no scores.
- No new dependencies; sync `def` endpoints; no git commits.

**Files to Create/Modify:**
- Create: `app/core/security.py`, `app/users/schemas.py`, `app/users/router.py`, `app/auth/__init__.py`, `app/auth/router.py`, `app/auth/dependencies.py`, `app/main.py`, `tests/test_auth.py`, `tests/test_users.py`
- Modify: `tests/conftest.py`

**Specification & Interface Requirements:**
- `hash_password`, `verify_password`, `create_access_token(subject, expires_delta=None)`, `decode_access_token(token) -> int`.
- `UserCreate(username: 3-50 [A-Za-z0-9_], email: validated + lowercased, password: 8-72)`.
- `UserRead(id, username, email, daily_study_hours, created_at)` — never `hashed_password`.
- `UserUpdate(daily_study_hours: 0.5-16.0 | None)`, `Token(access_token, token_type="bearer")`.
- Routes and status codes exactly as in `implementation.md` §5.

**Edge Cases You Must Cover:**
- [ ] `test_login_with_username_or_email`: registered `alex_dev` / `Alex@School.edu`; both login forms return 200.
- [ ] `test_duplicate_registration_is_409`: duplicate username AND duplicate email each return 409; hashes never compared in plaintext.
- [ ] `test_token_of_deleted_user_is_401`: token from before `DELETE /users/me` returns 401 afterwards.
- [ ] `test_user_read_never_returns_hash`: `hashed_password` absent from register, me, and patch responses.
- [ ] `test_delete_user_cascades_children`: after deletion, that user's courses/tasks are gone from `taskqueue_test`.
- [ ] `test_daily_study_hours_bounds`: 0.4 and 16.1 return 422; 0.5 and 16.0 succeed.
- [ ] `test_naive_or_malformed_email_password`: 422 for bad email, short password, invalid username.

**Step-by-Step Execution Plan:**
1. Write `tests/test_auth.py` and `tests/test_users.py` with the cases above.
2. Run `uv run pytest tests/test_auth.py tests/test_users.py -v` → expect FAIL (import errors).
3. Implement `app/core/security.py` and `app/users/schemas.py`.
4. Implement `app/auth/dependencies.py`, `app/auth/router.py`.
5. Implement `app/users/router.py`, `app/main.py`.
6. Extend `tests/conftest.py` with `client`, `make_user`, `auth_headers`.
7. Run `uv run pytest tests/test_auth.py tests/test_users.py -v` → expect PASS.
8. Run `uv run pytest -v` → expect all Day 1/2/3 tests PASS.

### Day 3 Definition of Done
- All edge-case tests pass; full suite green.
- No route reads headers or decodes tokens except `get_current_user`.
- No `hashed_password`, `SECRET_KEY`, or password appears in responses, logs, or git.
- No new Alembic revision; schema untouched.
- Owner commits on a feature branch; agent does not commit.
