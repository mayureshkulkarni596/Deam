# Deam | Smart Society Gate Management System

A local-first, AI-assisted visitor access system for residential societies. Deam is designed to combine visitor verification, resident approvals, an administrative dashboard, audit logging, and optional Arduino-controlled gate hardware in one privacy-conscious system.

> **Development status:** Early scaffold / Phase 0 in progress. The repository currently contains the initial health endpoint and mock gate-controller interface. Face verification, authentication, database-backed visitor workflows, the frontend, and real hardware integration are planned work and should not be considered implemented yet.

## Project goals

- **Verify visitors locally:** Use PIN checks and CPU-based face verification with OpenCV models, without relying on paid cloud AI APIs.
- **Support safe access decisions:** Registered visitors may be automatically allowed only when configured checks pass; unknown guests can be sent to residents for approval.
- **Keep gate control on the backend:** The frontend never sends hardware commands directly. Only the backend decision engine should be able to request gate operations.
- **Fail closed:** If verification, the database, the network, or the serial connection fails, the safe outcome is to keep the gate closed.
- **Run on a local network:** Host the application on a laptop or Raspberry Pi and let the kiosk, resident phones, and admin browser connect over the LAN.
- **Support hardware-free development:** A mock gate controller enables development and testing before the Arduino/servo/relay hardware is ready.

## Planned capabilities

### Visitor access
- Registered visitors such as household staff and regular visitors
- Static or daily PIN credentials
- Face-image quality checks and local face matching
- Optional visitor schedules and validity windows
- Guest entry requests with resident approval, rejection, and expiry
- Delivery passes as a later/stretch feature

### Resident and admin experience
- Resident dashboard for pending requests and visit history
- Visitor enrolment and credential management
- Administrative settings, audit history, and CSV export
- Live request updates through WebSockets
- Optional Telegram notifications, disabled by default

### Hardware integration
- Mock and serial gate-controller implementations behind one interface
- Configurable serial port and baud rate
- A documented Arduino communication protocol
- A short, bounded gate-open command and hardware-side automatic closing
- Optional message authentication for the hardware protocol

## Architecture

```text
 Kiosk browser       Resident phone       Admin browser
      |                    |                    |
      +--------- HTTPS / WebSocket over LAN ----+
                           |
                    FastAPI backend
                           |
       +-------------------+--------------------+
       |                   |                    |
  Decision engine      Face / PIN services   Database
       |
  Gate controller
   /          \
 Mock mode   Serial mode
                 |
             USB serial
                 |
          Arduino + servo/relay
```

**Security boundary:** Only the backend decision engine may request a gate operation. UI actions, face-model results, and optional language-model output must never independently authorize opening the gate.

## Technology stack

| Layer | Planned technology |
|---|---|
| Backend API | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| Persistence | SQLAlchemy 2.x, Alembic; SQLite for development/tests and MySQL 8 for production |
| Authentication | JWT, role-based authorization, Argon2id or bcrypt password hashing |
| Face verification | OpenCV with YuNet face detection and SFace recognition ONNX models |
| Hardware | pyserial; Arduino with servo or relay |
| Real-time updates | FastAPI WebSockets |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Testing and quality | pytest, httpx, Ruff; frontend component and end-to-end tests planned |
| Optional integrations | Local Ollama for extracting delivery details and Telegram notifications, both feature-flagged |

The stack above describes the intended architecture, not a claim that every dependency or feature is already present in the repository.

## Safety, security, and privacy

- **Fail-closed behavior:** errors and timeouts must never result in an open command.
- **Least privilege:** gate-controller access is restricted to the decision engine.
- **Credential protection:** never log PINs or secrets; store password hashes and protect visitor secrets.
- **Abuse prevention:** apply rate limits to failed PIN attempts and login attempts.
- **Data minimization:** face embeddings and snapshots are personal data. Provide consent information, access controls, retention rules, and deletion workflows.
- **Honest biometric limitations:** face matching without liveness detection can be fooled by a printed photo or screen. Resident approval and conservative defaults reduce risk but do not eliminate spoofing.
- **Secrets:** keep real credentials in local environment files; commit only safe example values.

This is a student project and should not be used to control a real entrance until the threat model, hardware safeguards, failure behavior, and end-to-end tests have been reviewed.

## Project roadmap

- [ ] **Phase 0: Foundation**: configuration, database setup and models, migrations, seed data, health endpoint, authentication/roles, logging, mock gate controller, and MySQL development configuration.
- [ ] **Phase 1: Core MVP**: PIN and face services, decision engine, kiosk endpoints, resident approval flow, expiry handling, WebSockets, audit logs, rate limiting, and snapshots.
- [ ] **Phase 2: Frontend MVP**: login, kiosk flow, resident dashboard, visitor management, and API integration.
- [ ] **Phase 3: Hardware integration**: serial controller, protocol, Arduino reference sketch, heartbeat/reconnect behavior, and protocol tests.
- [ ] **Phase 4: Admin and polish**: passes, settings, audit viewer, CSV export, responsive and error states.
- [ ] **Phase 5: Optional extensions**: local LLM extraction, Telegram, liveness model, calibration tools, benchmarks, and end-to-end tests.

## Getting started

### Prerequisites

- Python 3.11 or newer
- Git
- A modern browser
- Node.js/npm when the frontend is added
- Arduino hardware only for real serial mode; the planned mock mode is intended for development without hardware

### Run the current backend scaffold

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Ubuntu / macOS / GitHub Codespaces**
```bash
source .venv/bin/activate
```

Install the currently listed backend dependencies and start the API:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/health`. In GitHub Codespaces, open the forwarded port 8000 from the **Ports** panel. The health endpoint is the current smoke test; it does not mean the complete visitor-management system is ready.

### Tests

From the `backend/` directory, with dependencies installed:

```bash
pytest
```

The initial scaffold includes a health endpoint test. More service, API, security, and hardware-protocol tests will be added as the corresponding phases are implemented.

## Repository layout

```text
Deam/
├── backend/
│   ├── app/
│   │   ├── gate/          # Gate controller interface and mock controller
│   │   └── main.py        # Current FastAPI app and health endpoint
│   ├── storage/
│   │   └── snapshots/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── docs/
│   └── ARCHITECTURE.md
├── frontend/              # Frontend setup placeholder
├── hardware-spec/         # Hardware protocol placeholder
└── README.md
```

The tree will grow as each roadmap phase is implemented.

## Contribution workflow

1. Work in a focused branch for one feature or phase.
2. Keep hardware access behind the backend decision engine and gate-controller interface.
3. Add tests for success paths, denied requests, timeouts, and failure cases.
4. Never commit real secrets, visitor photographs, biometric data, or production database files.
5. Update documentation when behavior, setup commands, or security assumptions change.

## Project principles

**Local-first · Privacy-aware · Fail-closed · Testable without hardware · Built in phases**

