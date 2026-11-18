# WSL Setup Runbook — PrioQ (reusable)

This documents how this project was moved from Windows to a working WSL2/Linux environment. Reuse it for future projects that hit the same Windows tooling problems.

## Why we moved

On Windows, an Application Control (WDAC) policy blocked native binaries inside `.venv`:

- `sqlalchemy\_collections_cy.cp314-win_amd64.pyd` → `ImportError: DLL load failed ... An Application Control policy has blocked this file`
- `.venv\Scripts\pytest.exe` → `An Application Control policy has blocked this file`

A Linux virtualenv inside WSL uses `.so` files instead of `.pyd`, so the same dependencies import normally. `uv run` itself worked; the blocked files were the compiled Python extensions / executables.

## 0. Assumptions

- WSL2 with Ubuntu 24.04 is installed and running.
- The Windows project lives at `C:/Users/<you>/Documents/<project>`.
- `pyproject.toml` declares the required Python version and dependencies.
- MySQL 8 is available either inside WSL or on Windows.

All commands below are meant to be run **inside a WSL shell** (type `wsl` in PowerShell first), unless explicitly marked otherwise.

## 1. Confirm WSL

```bash
wsl --status          # run from PowerShell if needed
wsl -l -v
cat /etc/os-release | head -3
python3 --version
command -v uv || echo "uv not installed"
```

## 2. Networking (recommended for Windows <-> WSL access)

Windows `.wslconfig` used for this setup:

```ini
[wsl2]
memory=3GB
swap=2GB
networkingMode=mirrored
```

`networkingMode=mirrored` shares Windows loopback with WSL. Changes to `.wslconfig` require `wsl --shutdown` from PowerShell before they take effect. If you do not need Windows-side access to WSL services, this is optional.

## 3. Copy the project into the WSL filesystem

Keep the project under your WSL home (e.g. `~/prioq`), **not** under `/mnt/c/...`. Cross-filesystem I/O is slow and can cause permission issues.

```bash
mkdir -p ~/prioq
rsync -a \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  /mnt/c/Users/<you>/Documents/<project>/ \
  ~/prioq/
```

Never copy a Windows `.venv` into WSL — Windows `.pyd` files cannot load in Linux.

## 4. Install uv, pin Python, build the Linux venv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version

cd ~/prioq
uv python install 3.14          # use the version required by pyproject.toml
uv python pin 3.14
uv sync --frozen                # uses the existing uv.lock
```

If `uv sync --frozen` complains that the lockfile is out of date, run `uv sync` instead (it will rewrite `uv.lock`).

If `pyproject.toml` declares a build backend but there is no installable `src/<package>/__init__.py`, add this so uv treats the project as an app rather than a package:

```toml
[tool.uv]
package = false
```

## 5. Verify the tooling

```bash
cd ~/prioq
uv run python -V
uv run python -c 'import sqlalchemy, alembic, fastapi; print(sqlalchemy.__version__, alembic.__version__)'
uv run python -m pytest --version
```

All three should succeed. This is the check that proves the Windows Application Control problem is gone.

## 6. Database setup

First find out where MySQL actually runs. In this setup MySQL was **inside WSL**, listening on `127.0.0.1:3307` (not the Windows `127.0.0.11:3310` used by Workbench):

```bash
ss -ltnp | grep 3307
grep -R -E '^\s*(port|bind-address)' /etc/mysql/mysql.conf.d/ 2>/dev/null
ps aux | grep mysqld | grep -v grep
```

Create the project databases and a dedicated user (no tables or data are touched):

```bash
sudo mysql <<'SQL'
CREATE DATABASE IF NOT EXISTS taskqueue CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS taskqueue_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'taskqueue'@'localhost' IDENTIFIED BY '<password>';
CREATE USER IF NOT EXISTS 'taskqueue'@'127.0.0.1' IDENTIFIED BY '<password>';
GRANT ALL PRIVILEGES ON taskqueue.* TO 'taskqueue'@'localhost';
GRANT ALL PRIVILEGES ON taskqueue_test.* TO 'taskqueue'@'localhost';
GRANT ALL PRIVILEGES ON taskqueue.* TO 'taskqueue'@'127.0.0.1';
GRANT ALL PRIVILEGES ON taskqueue_test.* TO 'taskqueue'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL
```

Generate secrets without printing them, and write the project `.env`:

```bash
PW=$(openssl rand -hex 16)
SK=$(openssl rand -hex 32)
cat > .env <<EOF
SECRET_KEY=$SK
DATABASE_URL=mysql+pymysql://taskqueue:$PW@127.0.0.1:3307/taskqueue?charset=utf8mb4
TEST_DATABASE_URL=mysql+pymysql://taskqueue:$PW@127.0.0.1:3307/taskqueue_test?charset=utf8mb4
ACCESS_TOKEN_EXPIRE_DAYS=7
EOF
chmod 600 .env
git check-ignore .env
```

Rules learned here:

- `.env.example` is a **template** with blank values; runtime must read `.env`.
- MySQL accounts are host-specific: `'user'@'localhost'` and `'user'@'127.0.0.1'` are different accounts. Grant both if you are unsure which host MySQL will match.
- Test databases must be real MySQL databases ending in `_test`, never SQLite/in-memory.
- Here, `CREATE USER` had to run before `GRANT`; otherwise MySQL 8 returns `Error 1410: You are not allowed to create a user with GRANT`.

## 7. Verify DB connectivity without revealing secrets

```bash
cd ~/prioq
uv run python - <<'PY'
from dotenv import dotenv_values
import pymysql
from sqlalchemy.engine import make_url

values = dotenv_values(".env")
for key in ("DATABASE_URL", "TEST_DATABASE_URL"):
    url = make_url(values[key])
    conn = pymysql.connect(host=url.host, port=url.port, user=url.username,
                           password=url.password, database=url.database)
    with conn.cursor() as cur:
        cur.execute("SELECT DATABASE()")
        print(key, "CONNECT_OK", cur.fetchone()[0])
    conn.close()
PY
```

Expected output:

```
DATABASE_URL CONNECT_OK taskqueue
TEST_DATABASE_URL CONNECT_OK taskqueue_test
```

## 8. Run the test suite

```bash
cd ~/prioq
uv run python -m pytest -v
```

`uv run pytest` also works inside WSL; `python -m pytest` was used here because the Windows `pytest.exe` was blocked by policy.

## 9. Reusable checklist for the next project

1. `wsl -l -v` — confirm the WSL2 distro is running.
2. Copy the project into `~/<project>` with `rsync`, excluding `.venv` and caches.
3. Install uv in WSL; `uv python install <version>`; `uv python pin <version>`; `uv sync --frozen`.
4. Add `[tool.uv] package = false` if there is no installable `src/<package>` module.
5. Verify SQLAlchemy / Alembic / FastAPI imports.
6. Locate MySQL (WSL vs Windows) and its real host/port.
7. Create databases + dedicated user; write `.env` with `chmod 600`; confirm `git check-ignore .env`.
8. Verify both DB URLs connect without printing credentials.
9. Run `uv run python -m pytest -v`.

## Gotchas

- Do not reuse the Windows `.venv`, or any venv under `/mnt/c/...`.
- `.wslconfig` changes need `wsl --shutdown` before they apply.
- Windows Workbench connection details do not transfer to WSL: the host/port in `.env` must be reachable **from WSL**.
- All Python/package commands go through `uv`; no bare `python`, `pip`, or `poetry`.
- Never print or commit `.env`, passwords, or generated secrets.
- Keep the source tree inside the WSL ext4 filesystem, not `/mnt/c`.
