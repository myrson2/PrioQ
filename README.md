# Smart Student Task Prioritization Queue System

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![MySQL 8.0](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://www.mysql.com/)
[![uv](https://img.shields.io/badge/managed%20by-uv-purple.svg)](https://docs.astral.sh/uv/)

An intelligent task management and prioritization backend designed for students. Traditional task lists sort strictly by calendar deadlines, causing students to procrastinate on high-impact projects while exhausting energy on trivial, short-term assignments. 

This system uses a **multi-dimensional prioritization queue** that dynamically balances deadline urgency, student study bandwidth, grade impact, and task difficulty into an explainable 0–100 priority score.

---

## Key Features

- **Multi-Tenant Authentication:** Secure student registration and login with Argon2 password hashing and 7-day JWT bearer tokens.
- **Academic Course Management:** Organize coursework by classes (e.g., `CS 101`, `Math 201`) with customized hex color badges for visual rendering.
- **Dual Queue Prioritization:**
  - **Deadline Queue (`?sort=deadline`):** Chronological order (nearest deadline first).
  - **Smart Queue (`?sort=smart`):** Dynamic 0–100 score highlighting the highest-leverage tasks to tackle right now.
- **Explainable Scores:** Every score provides its full factor breakdown (`time_pressure`, `impact`, `difficulty_factor`, `hours_until_due`, `urgent`, `overdue`). No black-box magic.
- **Top Tasks View (`GET /tasks/top?n=3`):** Instant access to your top focus items for the day.
- **Zero Data Staleness:** Priority scores are calculated on-the-fly at read time from current time and remaining study hours—no stale scores stored in the database.
- **Privacy & IDOR Masking:** Strict multi-tenant isolation where foreign or missing resources uniformly return `404 Not Found`.

---

## Tech Stack

| Layer | Technology | Description |
|---|---|---|
| **Language & Tooling** | Python 3.12 + [uv](https://docs.astral.sh/uv/) | Fast, deterministic package management and virtual environments |
| **API Framework** | FastAPI + Pydantic v2 | High-performance asynchronous-ready REST framework with automatic Swagger docs |
| **Persistence** | SQLAlchemy 2.0 (Sync) | Robust ORM with explicit session lifecycle and domain models |
| **Database** | MySQL 8.0 (InnoDB, `utf8mb4`) | Relational database with full foreign key cascades |
| **Migrations** | Alembic | Declarative schema versioning |
| **Security** | PyJWT + `pwdlib[argon2]` | HS256 JWT tokens and Argon2 password hashing |
| **Testing** | pytest + HTTPX | Automated test suite running against an isolated MySQL test database |

---

## Project Structure

```
├── app/
│   ├── main.py                 # FastAPI application factory and router registration
│   ├── models.py               # Central declarative model exports
│   ├── core/
│   │   ├── config.py           # Typed environment settings (pydantic-settings)
│   │   ├── database.py         # SQLAlchemy engine, session maker, and UTCDateTime type
│   │   └── security.py         # Argon2 hashing and JWT token management
│   ├── auth/                   # Registration, login, and get_current_user dependency
│   ├── users/                  # User profile and /users/me endpoints
│   ├── courses/                # Course models, schemas, and /courses CRUD
│   └── tasks/                  # Task models, CRUD, pure scoring engine, and queue endpoints
├── alembic/                    # Database migrations
├── specs/                      # Project constitution, mission, roadmap, and feature specs
│   ├── constitution.md         # Core architectural non-negotiables
│   ├── mission.md              # Vision, target persona, and success metrics
│   ├── tech-stack.md           # Stack justifications and constraints
│   ├── roadmap.md              # Milestones (M1: Backend, M2: Frontend, M3: ML)
│   └── feature/                # Feature specification triads
├── tests/                      # Automated test suite
└── docs/superpowers/plans/     # Implementation plans
```

---

## Getting Started

### 1. Prerequisites
- **uv** package manager installed:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **MySQL 8.0** service running locally.

### 2. One-Time MySQL Database Setup
Run the following SQL commands in MySQL Workbench or via MySQL command line as `root`:
```sql
CREATE DATABASE taskqueue      CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE taskqueue_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE USER 'taskqueue'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON taskqueue.*      TO 'taskqueue'@'localhost';
GRANT ALL PRIVILEGES ON taskqueue_test.* TO 'taskqueue'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Update `.env` with your credentials:
```ini
SECRET_KEY=generate_a_random_secure_secret_key_here
DATABASE_URL=mysql+pymysql://taskqueue:your_secure_password@localhost:3306/taskqueue?charset=utf8mb4
TEST_DATABASE_URL=mysql+pymysql://taskqueue:your_secure_password@localhost:3306/taskqueue_test?charset=utf8mb4
ACCESS_TOKEN_EXPIRE_DAYS=7
```

### 4. Install Dependencies & Apply Migrations
```bash
# Sync virtual environment and dependencies
uv sync

# Apply database migrations
uv run alembic upgrade head
```

### 5. Run Development Server
```bash
uv run fastapi dev app/main.py
```
Open interactive Swagger documentation at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

---

## Running Automated Tests

The test suite runs against the dedicated `taskqueue_test` database (auto-truncating tables between tests to guarantee isolation):

```bash
uv run pytest -v
```

---

## API Summary

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Register new student account | No |
| `POST` | `/auth/login` | Login with username/email & password | No |
| `GET` | `/users/me` | Fetch authenticated student profile | Yes |
| `PATCH` | `/users/me` | Update daily study hours | Yes |
| `DELETE` | `/users/me` | Delete account and cascade all owned data | Yes |
| `GET` | `/courses` | List all courses owned by student | Yes |
| `POST` | `/courses` | Create new course (name, code, hex color) | Yes |
| `GET` | `/courses/{id}` | Get course details | Yes |
| `PATCH` | `/courses/{id}` | Update course metadata | Yes |
| `DELETE` | `/courses/{id}` | Delete course (sets linked tasks' course to null) | Yes |
| `GET` | `/tasks` | List tasks (`?sort=deadline|smart&course_id=...`) | Yes |
| `POST` | `/tasks` | Create task (optional `course_id`) | Yes |
| `GET` | `/tasks/top` | Get top `n` focus tasks (defaults to smart sort) | Yes |
| `GET` | `/tasks/{id}` | Get task details with priority breakdown | Yes |
| `PATCH` | `/tasks/{id}` | Update task or toggle completion status | Yes |
| `DELETE` | `/tasks/{id}` | Permanently delete task | Yes |

---

## Governance & Architecture

This repository strictly enforces the architectural invariants defined in [`specs/constitution.md`](file:///C:/Users/merss/Documents/Smart%20Student%20Task%20Prioritization%20Queue%20System/specs/constitution.md):
- **Axiom 1:** Explainable priority (never return an opaque rank).
- **Axiom 2 / S-3:** Privacy by default (cross-tenant access masked as 404).
- **Axiom 3:** Pure, test-first scoring engine.
- **S-1:** Single auth gateway (`get_current_user`).
- **D-1 / D-5:** MySQL 8 throughout; priority scores are computed at read time and never persisted.
