# Day 3 — Authentication & Profile Service — Specification

**Feature folder:** `specs/feature/2026-11-19-day3-auth-users/`  
**Milestone:** M1 (see [specs/roadmap.md](../../roadmap.md))  
**Governed by:** [specs/constitution.md](../../constitution.md) and [specs/tech-stack.md](../../tech-stack.md)

---

## 1. Context & Motivation
Day 1 delivered typed settings, the `UTCDateTime` decorator, and the pure scoring engine. Day 2 delivered the three MySQL tables, the initial Alembic revision, and a guarded test harness. Nothing authenticates a student yet. Day 3 introduces the single identity gateway every later protected route will depend on: Argon2 password hashing, HS256 JWT bearer tokens, registration, flexible login, and the `/users/me` profile lifecycle. Day 4 (course/task CRUD) depends entirely on this work.

## 2. Approaches Considered & Decision
- **Approach 1 (Session cookies):** rejected — the M2 frontend is a separate origin and Swagger needs a simple bearer flow.
- **Approach 2 (JWT bearer + Argon2 — SELECTED):** `pwdlib[argon2]` hashes, PyJWT HS256 tokens with `sub = str(user.id)`, 7-day expiry. Works with Swagger "Authorize" and a decoupled frontend.
- **Approach 3 (Third-party OAuth/identity provider):** rejected — out of scope for a personal M1 backend and adds external dependencies.

## 3. Goals, Non-goals, and Anti-goals
### Goals
- Argon2 hashing and JWT encode/decode helpers in `app/core/security.py`.
- `POST /auth/register`, `POST /auth/login` (username OR email in the OAuth2 `username` field).
- `get_current_user` as the single auth gateway (S-1).
- `GET /users/me`, `PATCH /users/me`, `DELETE /users/me`.
- FastAPI entrypoint `app/main.py` registering auth and users routers.
- Failure cases tested: duplicates (409), bad credentials (401), deleted-user token (401).
### Non-goals
- Course and task routers (Day 4), queue endpoints (Day 5).
- New database columns, new Alembic revision, soft deletion, refresh tokens, email verification.
- Frontend, CORS, deployment, Redis, ML.
### Anti-goals
- No password hash or secret in any API response or log.
- No route reading `Authorization` or decoding JWT itself.
- No naive datetime accepted or produced.

## 4. User Stories
- **US-1 Register:** GIVEN a new student WHEN they POST a valid username, email, and password THEN an account is created with `daily_study_hours = 3.0` and `hashed_password` is an Argon2 hash, returning `201 UserRead`.
- **US-2 Flexible Login:** GIVEN a registered student WHEN they POST their username OR email (case-insensitive) plus password to `/auth/login` THEN they receive `200 {access_token, token_type: "bearer"}`.
- **US-3 Read Profile:** GIVEN a valid bearer token WHEN the student GETs `/users/me` THEN their own profile is returned without `hashed_password`.
- **US-4 Update Study Hours:** GIVEN a valid token WHEN the student PATCHes `daily_study_hours` between 0.5 and 16.0 THEN the profile updates and returns `200`.
- **US-5 Delete Account:** GIVEN a valid token WHEN the student DELETEs `/users/me` THEN the user, their courses, and their tasks are removed by the Day 2 `ON DELETE CASCADE` FKs, returning `204`.
- **US-6 Stale Token:** GIVEN a token issued before account deletion WHEN that token is reused THEN `/users/me` returns `401`, identical to any invalid token.

## 5. Functional Requirements
- **FR-1 Security helpers (`app/core/security.py`):** `hash_password(password: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`, `create_access_token(subject: int, expires_delta: timedelta | None = None) -> str`, `decode_access_token(token: str) -> int`. JWT HS256; `sub = str(user_id)`; `exp = now + ACCESS_TOKEN_EXPIRE_DAYS` (default 7).
- **FR-2 Register:** `POST /auth/register` accepts `UserCreate` with `username` 3–50 chars `[A-Za-z0-9_]+`, `email` validated and lowercased, `password` 8–72 chars. Success `201 UserRead`. Duplicate username or email returns `409` with `{"detail":"Username already taken"}` or `{"detail":"Email already registered"}`.
- **FR-3 Login:** `POST /auth/login` uses `OAuth2PasswordRequestForm` (`username` accepts username OR email, case-insensitive). Success `200 Token`. Any credential failure returns `401 {"detail":"Incorrect username/email or password"}`.
- **FR-4 Single gateway:** `app/auth/dependencies.py:get_current_user` is the only resolver of user identity. Routes declare `CurrentUser` via `Depends(get_current_user)`. Invalid, expired, or stale tokens return `401 {"detail":"Could not validate credentials"}` with `WWW-Authenticate: Bearer`.
- **FR-5 Profile:** `GET /users/me -> 200 UserRead`; `PATCH /users/me` accepts `UserUpdate(daily_study_hours: float | None)` bounded 0.5–16.0 and returns `200 UserRead`.
- **FR-6 Deletion:** `DELETE /users/me -> 204`. The route deletes the `User` row in the guarded session; Day 2 FKs cascade courses and tasks.
- **FR-7 App entrypoint:** `app/main.py` creates `FastAPI()` and includes auth and users routers.
- **FR-8 Test harness:** extend `tests/conftest.py` with `client`, `make_user`, and `auth_headers` fixtures built on the existing guarded `test_engine`; add `tests/test_auth.py` and `tests/test_users.py`.

## 6. Non-Functional Requirements
- **Security:** Argon2 hashes; `SECRET_KEY` from settings; no secrets in logs/git; hashed password never serialized (S-4).
- **Data integrity:** no schema change; MySQL 8 / InnoDB / utf8mb4; `Double` study hours; `UTCDateTime` timestamps (D-1, D-4).
- **Privacy:** no ID-based user routes; identity derived only from the token (Axiom 2 / S-3).
- **Tooling:** every command via `uv run`; sync `def` endpoints only.

## 7. Acceptance Criteria Checklist
- [ ] `POST /auth/register` creates a user with a non-plaintext hash and returns `201`.
- [ ] Duplicate username/email each return `409`; malformed input returns `422`.
- [ ] Login works with username and with email, case-insensitively.
- [ ] Bad credentials/expired tokens/stale tokens all return `401` with the specified detail.
- [ ] `GET/PATCH/DELETE /users/me` work with a valid token and never expose `hashed_password`.
- [ ] Deleting the account removes courses and tasks via cascade; the old token then returns `401`.
- [ ] `uv run pytest -v` green including Day 1/2 regressions.
