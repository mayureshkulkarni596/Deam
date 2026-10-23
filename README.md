# Deam | Smart Society Gate Management System

A local-first, AI-assisted visitor access system for residential societies. The project is designed to combine visitor verification, resident approvals, administrative tools, audit history, and optional Arduino-controlled gate hardware on a local network.

> **Status: Phase 0 foundation committed.** The repository now contains configuration, a FastAPI backend, SQLAlchemy account model, Alembic initial migration, password hashing and JWT helpers, role-checking dependencies, liveness/readiness endpoints, a mock gate-controller interface, seed-account tooling, and initial tests. Visitor workflows, face matching, PIN verification, frontend screens, and physical serial integration are not implemented yet.

## Core principles

- **Local-first:** run on a laptop or Raspberry Pi and serve kiosk, resident, and admin browsers over the local network.
- **Fail-closed:** if verification, the database, network, or hardware communication fails, the gate must remain closed.
- **Backend-controlled hardware:** the frontend never sends commands to Arduino. Only the future backend decision engine may request gate operations.
- **Hardware-free development:** the mock controller supports early testing without an Arduino attached.
- **Privacy-aware:** biometric data and visitor snapshots require consent, access controls, retention limits, and deletion workflows.
- **Open and student-friendly:** free/open-source components, documented setup, tests, and staged implementation.

## Planned functionality

### Visitor access
- Registered visitors with static or daily PIN credentials
- Local CPU face verification using OpenCV YuNet and SFace models
- Visitor schedules and validity windows
- Guest requests sent to residents for approval, rejection, or expiry
- Delivery passes as a later-phase feature

### Resident and admin tools
- Resident dashboard, pending requests, and visit history
- Visitor enrolment and credential management
- Admin settings, audit viewer, and CSV export
- Real-time updates through WebSockets
- Optional Telegram notifications, disabled by default

### Gate hardware
- Mock and serial implementations behind one GateController interface
- Configurable serial port and baud rate
- Planned Arduino protocol with acknowledgements, timeout handling, replay protection, heartbeat, and hardware-side auto-close

## Architecture

```text
Kiosk browser     Resident phone     Admin browser
      \                 |                  /
       +---------- local network ----------+
                         |
                    FastAPI API
                         |
          +--------------+-------------+
          |              |             |
      Auth / roles   Future decision  SQLAlchemy
                         engine          |
                          |        SQLite / MySQL 8
                     GateController
                      /          \
                   Mock        Serial (planned)
                                  |
                             Arduino + servo/relay
```

**Safety boundary:** the browser cannot open the gate. The future decision engine is the only component allowed to call a gate controller. Optional AI assistance may extract delivery details later, but it must never decide whether the gate opens.

## Technology

| Layer | Intended technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| Data | SQLAlchemy 2.x, Alembic, SQLite for development/tests, MySQL 8 for deployment |
| Authentication | JWT bearer tokens, Argon2id password hashing, role dependencies |
| Face AI | OpenCV with YuNet detector and SFace recognizer ONNX models |
| Hardware | pyserial and Arduino servo/relay |
| Real-time | FastAPI WebSockets |
| Frontend (planned) | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Quality | pytest, httpx, Ruff |
| Optional integrations | Local Ollama and Telegram behind feature flags |

The table describes the intended full project stack. Only the Phase 0 subset listed in the status section is currently implemented.

## Phase 0: Foundation

Implemented in the repository:
- Typed environment configuration and safe example settings
- FastAPI app, CORS allowlist, and startup/shutdown logging
- SQLAlchemy engine/session lifecycle and initial User model
- Alembic migration for the users table
- Argon2 password hashing and short-lived JWT helper functions
- Authentication login endpoint and role-checking dependencies
- Liveness and database-readiness endpoints
- Mock gate interface and failure simulation
- Seed script requiring passwords to be supplied via environment variables
- Initial health, authentication, and mock-controller tests
- MySQL 8 Docker Compose service

Still to do in later phases: login rate limiting, audit events, visitor and PIN models, decision engine, face model setup, kiosk/resident UI, and real hardware serial communication.

## Quick start: Windows, Linux, or Codespaces

### 1. Prerequisites

- Python 3.11 or newer
- Git
- Internet access for installing Python dependencies
- Docker only if you want to run MySQL; SQLite is the default for development

### 2. Create and activate a virtual environment

From the repository root:

**Windows PowerShell**
```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Ubuntu / Codespaces**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies and configure environment

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy the example settings file:

**PowerShell**
```powershell
Copy-Item .env.example .env
```

**Ubuntu / Codespaces**
```bash
cp .env.example .env
```

Before using the app beyond local development, replace JWT_SECRET with a long random secret. Never commit .env or real credentials. SQLite is used by default.

### 4. Create the database schema

From the backend directory, with the virtual environment active:

```bash
alembic upgrade head
```

### 5. Seed development accounts

Set two passwords of at least 12 characters. Do not paste real or reused passwords into source files.

**PowerShell**
```powershell
$env:SEED_ADMIN_PASSWORD = "replace-with-a-unique-admin-password"
$env:SEED_RESIDENT_PASSWORD = "replace-with-a-unique-resident-password"
python scripts/seed.py
```

**Ubuntu / Codespaces**
```bash
export SEED_ADMIN_PASSWORD='replace-with-a-unique-admin-password'
export SEED_RESIDENT_PASSWORD='replace-with-a-unique-resident-password'
python scripts/seed.py
```

The seed script creates admin@example.test and resident@example.test unless you override the email variables. These are example identities, not preconfigured passwords. Use the same passwords you supplied above when testing login.

### 6. Start the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:
- `http://127.0.0.1:8000/health` for liveness
- `http://127.0.0.1:8000/health/ready` for database readiness
- `http://127.0.0.1:8000/docs` for the interactive API docs

In GitHub Codespaces, open the **Ports** panel and use the forwarded port 8000 URL. Keep it private; do not expose development authentication endpoints publicly.

### 7. Run tests and lint

From the backend directory:

```bash
pytest
ruff check app scripts tests
```

The repository includes initial tests for health/readiness, login behavior, and mock-gate success/failure. Run them in your environment after installing dependencies; CI/test execution has not been verified from this chat.

## Optional MySQL 8

Docker Compose binds MySQL to localhost only. Set both MYSQL_PASSWORD and MYSQL_ROOT_PASSWORD before starting it.

**PowerShell**
```powershell
$env:MYSQL_PASSWORD = "replace-with-a-unique-db-password"
$env:MYSQL_ROOT_PASSWORD = "replace-with-a-unique-root-password"
docker compose up -d mysql
```

**Ubuntu / Codespaces**
```bash
export MYSQL_PASSWORD='replace-with-a-unique-db-password'
export MYSQL_ROOT_PASSWORD='replace-with-a-unique-root-password'
docker compose up -d mysql
```

Then set DATABASE_URL in backend/.env to a MySQL URL such as `mysql+pymysql://deam_app:URL_ENCODED_PASSWORD@127.0.0.1:3306/deam` and run `alembic upgrade head` again. URL-encode special characters in the password. SQLite is simpler for the initial phase.

## Roadmap

- [x] **Phase 0: Foundation** - configuration, database foundation and migration, seed script, health endpoints, authentication helpers, roles, logging, mock gate interface, MySQL compose, initial tests
- [ ] **Phase 1: Core MVP** - PIN and face services, decision engine, kiosk endpoints, resident approvals, expiry sweeper, WebSockets, audit trail, rate limits, snapshots
- [ ] **Phase 2: Frontend MVP** - login, kiosk flow, resident dashboard, visitor manager, API integration
- [ ] **Phase 3: Hardware integration** - serial controller, protocol, Arduino reference sketch, heartbeat/reconnect, protocol tests
- [ ] **Phase 4: Admin and polish** - passes, settings, audit viewer, CSV export, responsive and error states
- [ ] **Phase 5: Optional extensions** - local LLM parsing, Telegram, liveness model, calibration, benchmarks, end-to-end tests

## Security and privacy limitations

- Face matching without liveness detection can be fooled by a printed photo or screen. A future implementation must disclose this limitation and use conservative approval defaults.
- Six-digit PINs require strict rate limiting and a mandatory second factor; hashing alone does not prevent brute force.
- Visitor snapshots and face embeddings are personal data. The completed system must implement consent, retention, deletion, and access-control workflows.
- The current Phase 0 backend is a development foundation, **not a production access-control system**. Do not connect it to a real gate until the decision engine, serial protocol, failure behavior, and security tests are implemented and reviewed.

## Contributing

1. Work in a focused branch and keep changes small enough to review.
2. Add tests for successful, denied, and failure cases.
3. Never commit .env files, credentials, real visitor photos, embeddings, or database files.
4. Keep all hardware access behind the backend decision engine.
5. Update documentation when setup commands, behavior, or security assumptions change.

**Local-first · Privacy-aware · Fail-closed · Testable without hardware · Built in phases**
