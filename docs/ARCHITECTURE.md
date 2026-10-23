# Deam Architecture

## Phase 0 boundary

Phase 0 establishes configuration, SQLAlchemy sessions, the initial account model and migration, password hashing, JWT helpers, role dependencies, health/readiness endpoints, console logging, mock gate control, and MySQL development configuration.

Visitor records, face recognition, PIN validation, resident approvals, and physical serial communication are not implemented yet.

## Trust boundary

```text
Kiosk / Resident / Admin browser
             |
          HTTP API
             |
        FastAPI backend ------ SQLAlchemy ------ SQLite or MySQL 8
             |
       Authentication / role checks
             |
       Future decision engine (only module allowed to request gate operations)
             |
         GateController interface
           /              \
       Mock mode       Serial mode (planned)
```

The frontend must never communicate directly with Arduino hardware. Only the future decision engine may call a gate controller. Any error or timeout must deny or fail an access request, never cause an opening.

Use timezone-aware timestamps where supported and normalize application logic to UTC. Display times in APP_TIMEZONE, defaulting to Asia/Kolkata. Roles are admin and resident. Passwords use Argon2id hashes and JWTs are short-lived.

This scaffold is not yet suitable for a real entrance. Later phases must add rate limiting, HTTPS for LAN camera use, audit logging, visitor consent and retention, serial protocol authentication, and failure-injection tests.
