# Day 2 — Database Models & Migration Harness — Validation

**Feature folder:** `specs/feature/2026-11-19-day2-models-migrations/`  
**Milestone:** M1 (see [`specs/roadmap.md`](specs/roadmap.md))  
**Governed by:** [`specs/constitution.md`](specs/constitution.md) and [`specs/tech-stack.md`](specs/tech-stack.md)

---

## 1. Automated Test Matrix (`uv run pytest`)
| Test file | Coverage target | Key cases |
|---|---|---|
| `tests/test_core.py` (Day 1, regression) | Settings & UTC types | Secret required, 7-day default, offset→naive UTC, naive rejection, aware UTC on read. |
| `tests/test_scoring.py` (Day 1, regression) | Pure scoring | A=20.2, B=56.1, C=64.5, 24h boundary, completed→`None`, sort order. |
| `tests/test_migrations.py` | Schema & harness | `test_upgrade_creates_expected_tables`; `test_foreign_keys_use_cascade_and_set_null`; `test_double_and_datetime_columns`; `test_test_database_name_is_guarded`; `test_upgrade_downgrade_cycle`. |

## 2. Reference Fixtures (schema facts)
| Object | Expected value |
|---|---|
| Databases | `taskqueue` (app), `taskqueue_test` (tests; `_test` suffix mandatory) |
| Tables after upgrade | `users`, `courses`, `tasks`, `alembic_version` |
| `users.id` FK action | `ON DELETE CASCADE` from `courses.owner_id`, `tasks.owner_id` |
| `courses.id` FK action | `ON DELETE SET NULL` on `tasks.course_id` |
| Float columns | `DOUBLE` (`grade_weight`, `estimated_hours`, `daily_study_hours`) |
| Timestamp columns | `DATETIME(6)` via `UTCDateTime` |
| Category column | `VARCHAR(20)` + check constraint, five allowed values |

## 3. Mandatory Constitution Compliance Matrix
| Rule ID | Invariant | How Day 2 enforces it | Verified by |
|---|---|---|---|
| **Axiom 1** | Explainable priority | No scores returned or stored today; scoring module untouched. | `tests/test_scoring.py` regression |
| **Axiom 2 / S-3** | Privacy & 404 masking | Ownership FKs in schema; no endpoints yet to leak cross-tenant data. | `test_foreign_keys_use_cascade_and_set_null` |
| **Axiom 3** | Pure, test-first scoring | `app/tasks/scoring.py` unchanged; all new logic schema-only. | `tests/test_scoring.py` |
| **S-1** | Single auth gateway | No protected routes added today. | Code inspection |
| **S-2** | Ownership in the query | `owner_id` columns indexed and FK-constrained for Day 4 service filters. | `test_foreign_keys_use_cascade_and_set_null` |
| **S-4** | Credentials | No credentials in models, migration, tests, or docs; `.env` stays ignored. | Code + doc inspection |
| **S-5** | Least-privilege DB user | Dedicated `taskqueue` MySQL user in `.env`; no root in app runtime. | Readiness check |
| **D-1** | MySQL 8 everywhere | InnoDB / `utf8mb4`; both DBs checked at start; no SQLite. | Readiness check, `tests/conftest.py` |
| **D-2** | Migrations only | Single Alembic revision; no `create_all` anywhere. | `test_upgrade_creates_expected_tables` |
| **D-3** | Cascading FKs | User cascade + course set-null declared in models and migration. | `test_foreign_keys_use_cascade_and_set_null` |
| **D-4** | UTC discipline | All date columns use `UTCDateTime` (`DATETIME(6)`); naive values rejected at bind. | `test_double_and_datetime_columns`, Day 1 `test_core.py` |
| **D-5** | Scores not persisted | No priority/score columns in the three tables. | `test_upgrade_creates_expected_tables`, schema audit |
| **D-6** | Edge validation | Explicit VARCHAR lengths, NOT NULL, FKs, enum check constraint. | `test_double_and_datetime_columns` |
| **M1 scope** | Out-of-scope discipline | No Docker, Redis, ML, frontend, email, or routers in this suite. | File inventory |

## 4. Manual QA & Exploratory Runbook
1. Run the readiness check; confirm `taskqueue_test` prints.
2. Run `uv run alembic upgrade head`; inspect `taskqueue` in MySQL Workbench: three tables, `utf8mb4`, FKs present.
3. Insert a test user, course, and task in `taskqueue_test`; delete the course and verify the task survives with `course_id = null`; delete the user and verify all rows disappear.
4. Temporarily point `TEST_DATABASE_URL` at a non-`_test` name and confirm pytest aborts before any DELETE; restore it afterwards.
5. Run `uv run alembic downgrade base`, then `uv run alembic upgrade head`, then `uv run pytest -v` and confirm everything passes again.
