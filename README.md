# ct-backend

FastAPI backend for Creator Tools — JWT auth, SQLAlchemy 2.0, structured logging, rate limiting.

| | |
|---|---|
| **Python** | 3.10 · 3.11 · 3.12 |
| **Poetry** | 1.8.x |
| **Port** | 8000 |
| **API docs** | `http://localhost:8000/docs` _(requires `DEBUG=true`)_ |

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | **≥ 3.10** | 3.10, 3.11, and 3.12 all tested |
| Poetry | **1.8.x** | Dependency + virtualenv manager |
| Docker Desktop | ≥ 4.x | Only needed for the Docker path |
| PostgreSQL | ≥ 14 | Only needed if not using SQLite or Docker |

---

## Git & Repository

```bash
# Clone this repo
git clone https://github.com/prateek099/ct-backend.git
cd ct-backend

# Check status of working tree
git status

# Stage and commit changes
git add <file>                         # stage a specific file
git add -p                             # interactively stage hunks
git commit -m "feat: describe change"

# Push to remote
git push origin main

# Create and switch to a feature branch
git checkout -b feat/my-feature

# Pull latest changes
git pull origin main

# Merge feature branch into main
git checkout main
git merge feat/my-feature

# Delete a branch after merging
git branch -d feat/my-feature          # local
git push origin --delete feat/my-feature  # remote
```

---

## Quick Start — no Docker, SQLite (fastest)

Works on Mac and Windows. No database setup required.

```bash
git clone https://github.com/prateek099/ct-backend.git ct-backend && cd ct-backend
cp .env.example .env          # Windows: Copy-Item .env.example .env
poetry install
poetry run uvicorn app.main:app --reload
```

Server → `http://localhost:8000`  
Health check → `http://localhost:8000/health`

Set `DEBUG=true` in `.env` to enable Swagger at `http://localhost:8000/docs`.

---

## Without Docker

### Mac

**1 — Install Python 3.12 (or 3.10 / 3.11)**

```bash
brew install python@3.12
python3 --version           # Python 3.12.x
```

Or download the installer from [python.org/downloads](https://www.python.org/downloads/).

**2 — Install Poetry 1.8.x**

```bash
curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.4 python3 -
```

Poetry installs to `~/.local/bin`. Add it to your PATH (add to `~/.zshrc` or `~/.bashrc`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Restart your terminal, then verify:

```bash
poetry --version            # Poetry (version 1.8.4)
```

**3 — Clone and install dependencies**

```bash
git clone https://github.com/prateek099/ct-backend.git ct-backend
cd ct-backend
poetry install              # creates .venv, installs all deps from poetry.lock
```

**4 — Configure environment**

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```dotenv
DEBUG=true
JWT_SECRET_KEY=<run: openssl rand -hex 32>
```

**5 — Run the server**

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**6 — Run tests**

```bash
poetry run pytest
poetry run pytest -v        # verbose
```

---

### Windows (PowerShell)

**1 — Install Python 3.12 (or 3.10 / 3.11)**

Download and run the installer from [python.org/downloads](https://www.python.org/downloads/).  
✅ Check **"Add Python to PATH"** during installation.

```powershell
python --version            # Python 3.12.x
```

**2 — Install Poetry 1.8.x**

```powershell
$env:POETRY_VERSION = "1.8.4"
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

Add Poetry to your PATH (the installer prints the exact path, typically `%APPDATA%\Python\Scripts`):

```powershell
$env:PATH += ";$env:APPDATA\Python\Scripts"
```

To make it permanent, add to your PowerShell profile:

```powershell
notepad $PROFILE
# Add: $env:PATH += ";$env:APPDATA\Python\Scripts"
```

Restart PowerShell, then verify:

```powershell
poetry --version            # Poetry (version 1.8.4)
```

**3 — Clone and install dependencies**

```powershell
git clone https://github.com/prateek099/ct-backend.git ct-backend
cd ct-backend
poetry install
```

**4 — Configure environment**

```powershell
Copy-Item .env.example .env
notepad .env                # set DEBUG=true and JWT_SECRET_KEY
```

Generate a secret key on Windows:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**5 — Run the server**

```powershell
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**6 — Run tests**

```powershell
poetry run pytest
```

---

### Switch to PostgreSQL (without Docker)

The default database is SQLite (`ct.db` in the project root). To use PostgreSQL:

**1 — Create a database and user**

```sql
CREATE DATABASE ct_db;
CREATE USER ct_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE ct_db TO ct_user;
```

**2 — Update `DATABASE_URL` in `.env`**

```dotenv
# Uses psycopg3 — prefix must be postgresql+psycopg:// (NOT psycopg2)
DATABASE_URL=postgresql+psycopg://ct_user:yourpassword@localhost:5432/ct_db
```

**3 — Apply migrations (if any exist)**

```bash
poetry run alembic upgrade head
```

Tables are also created automatically on startup via `Base.metadata.create_all`.

---

## With Docker

Docker Desktop must be running (`docker info` should succeed).

### Option A — SQLite (single container, zero setup)

Create `docker-compose.yml` in the project root:

```yaml
services:
  api:
    build:
      context: .
      target: development
    ports:
      - "8000:8000"
      - "5678:5678"       # debugpy — attach VS Code debugger
    volumes:
      - .:/app
      - /app/.venv        # preserve virtualenv inside container
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite:///./ct.db
```

### Option B — PostgreSQL (two containers)

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ct_db
      POSTGRES_USER: ct_user
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ct_user"]
      interval: 5s
      retries: 5

  api:
    build:
      context: .
      target: development
    ports:
      - "8000:8000"
      - "5678:5678"
    volumes:
      - .:/app
      - /app/.venv
    env_file:
      - .env
    environment:
      # Overrides DATABASE_URL from .env — uses the db service above
      - DATABASE_URL=postgresql+psycopg://ct_user:secret@db:5432/ct_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

### Start (Mac and Windows — same command)

```bash
cp .env.example .env        # Windows: Copy-Item .env.example .env
docker compose up --build
```

Add `-d` to run in the background:

```bash
docker compose up --build -d
docker compose logs -f api  # tail logs
```

### Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","app":"Creator Tools API","env":"development"}
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Creator Tools API` | Name shown in API responses |
| `DEBUG` | `false` | `true` → enables `/docs` and `/redoc` |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `DATABASE_URL` | `sqlite:///./ct.db` | SQLite or `postgresql+psycopg://…` |
| `JWT_SECRET_KEY` | _(insecure default)_ | **Change in production.** Use `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed frontend origins |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `LOG_FORMAT` | `json` | `pretty` (coloured, local) \| `json` (structured, prod) |

---

## Project structure

```
ct-backend/
├── app/
│   ├── main.py                  # App factory — middleware, routes, handlers
│   ├── api/
│   │   ├── deps.py              # get_current_user JWT dependency
│   │   └── routes/
│   │       ├── auth.py          # POST /auth/register /login /refresh  GET /auth/me
│   │       └── users.py         # CRUD /users/* (all protected)
│   ├── core/
│   │   ├── config.py            # pydantic-settings — reads .env
│   │   ├── database.py          # SQLAlchemy engine, session, Base
│   │   ├── exceptions.py        # AppError subclasses + global handlers
│   │   ├── logging.py           # loguru setup, stdlib interception
│   │   └── security.py          # bcrypt hashing, JWT encode/decode
│   ├── middleware/
│   │   ├── request_id.py        # X-Request-ID on every request
│   │   ├── timing.py            # X-Process-Time header
│   │   └── logging.py           # per-request structured log
│   ├── models/
│   │   └── user.py              # SQLAlchemy User model
│   ├── schemas/
│   │   ├── auth.py              # LoginRequest, RegisterRequest, TokenResponse
│   │   └── user.py              # UserCreate, UserResponse
│   └── services/
│       ├── auth_service.py      # register, login, refresh_tokens
│       └── user_service.py      # CRUD — raises AppError subclasses
├── tests/
│   ├── conftest.py              # Fixtures: client, registered_user, auth_headers
│   ├── test_auth.py
│   └── test_users.py
├── .env.example                 # Environment template — copy to .env
├── Dockerfile                   # Multi-stage: base / development / production
├── poetry.lock                  # Pinned dependency tree — commit this file
├── pyproject.toml               # Poetry config + tool settings
└── README.md
```

---

## Dev commands

```bash
# Start server with hot reload
poetry run uvicorn app.main:app --reload

# Run all tests
poetry run pytest

# Run a single test file
poetry run pytest tests/test_auth.py -v

# Format code
poetry run black app tests
poetry run isort app tests

# Check formatting without writing
poetry run black --check app tests

# Add a runtime dependency
poetry add <package>

# Add a dev-only dependency
poetry add --group dev <package>

# Show installed packages
poetry show

# Generate an Alembic migration
poetry run alembic revision --autogenerate -m "describe change"

# Apply all pending migrations
poetry run alembic upgrade head

# Rollback one migration
poetry run alembic downgrade -1
```

---

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Health check |
| `POST` | `/api/v1/auth/register` | — | Register a new user |
| `POST` | `/api/v1/auth/login` | — | Login → access + refresh tokens |
| `POST` | `/api/v1/auth/refresh` | — | Exchange refresh token for new pair |
| `GET` | `/api/v1/auth/me` | Bearer | Current user profile |
| `GET` | `/api/v1/users/` | Bearer | List all users |
| `POST` | `/api/v1/users/` | Bearer | Create a user |
| `GET` | `/api/v1/users/{id}` | Bearer | Get user by ID |
| `DELETE` | `/api/v1/users/{id}` | Bearer | Delete user by ID |

Full interactive docs available at `/docs` when `DEBUG=true`.

---

## Troubleshooting

**`poetry: command not found`**

Poetry's bin directory is not on your PATH.

```bash
# Mac / Linux — add to ~/.zshrc or ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"

# Windows PowerShell
$env:PATH += ";$env:APPDATA\Python\Scripts"
```

---

**`ModuleNotFoundError: No module named 'app'`**

Always run commands through Poetry, not bare `python`:

```bash
poetry run uvicorn app.main:app --reload
# or activate the shell first:
poetry shell
uvicorn app.main:app --reload
```

---

**`TypeError: connect() got an unexpected keyword argument 'check_same_thread'`**

You are pointing at PostgreSQL but running an older version of `database.py` that passed a SQLite-only argument to the engine. Pull the latest code — `database.py` now makes `connect_args` conditional.

---

**`sqlalchemy.exc.OperationalError: unable to open database file`**

Run the server from the project root, or use an absolute path:

```dotenv
DATABASE_URL=sqlite:////tmp/ct.db
```

---

**`psycopg.OperationalError: connection refused`**

PostgreSQL is not running or the credentials are wrong. Test the connection directly:

```bash
psql postgresql+psycopg://ct_user:yourpassword@localhost:5432/ct_db
# or
psql -h localhost -U ct_user -d ct_db
```

---

**`/docs` returns 404**

Swagger is disabled unless `DEBUG=true`. Set it in `.env` and restart:

```dotenv
DEBUG=true
```

---

**Port 8000 already in use**

```bash
# Mac / Linux
lsof -ti:8000 | xargs kill

# Windows PowerShell
netstat -ano | findstr :8000
# then: taskkill /PID <pid> /F
```

---

**`jose.exceptions.JWTError: Signature verification failed`**

The `JWT_SECRET_KEY` changed after tokens were issued. Log out, log back in for a fresh pair.
