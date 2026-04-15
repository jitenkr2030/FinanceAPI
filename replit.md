# Finance API SaaS

A FastAPI-based backend for managing financial operations including invoicing, accounting, tax calculations, and reporting.

## Architecture

- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0
- **Validation:** Pydantic v2
- **Database:** PostgreSQL (via `DATABASE_URL` env var), falls back to SQLite
- **Web Server (dev):** Uvicorn with hot reload
- **Web Server (prod):** Gunicorn

## Project Structure

```
app/
  main.py           - FastAPI app entry point, creates DB tables
  core/
    config.py       - Settings (env vars, DB URL, secret key)
    deps.py         - FastAPI dependencies (API key auth)
    security.py     - API key generation/verification
  db/
    base.py         - SQLAlchemy declarative base
    session.py      - DB engine, session factory, get_db dependency
  models/           - SQLAlchemy ORM models (User, Invoice, Tax, Ledger, etc.)
  schemas/          - Pydantic v2 request/response schemas
  routes/v1/        - API route handlers (auth, invoice, tax, accounting, audit, report)
  services/         - Business logic layer
  admin/            - SQLAdmin panel placeholder
```

## Running the App

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

## API Endpoints

All endpoints are prefixed with `/api/v1`.

- `POST /api/v1/auth/register` - Register a user, returns API key
- `POST /api/v1/invoice/create` - Create an invoice
- `GET /api/v1/invoice/list` - List invoices
- `POST /api/v1/tax/calculate` - Calculate tax
- `POST /api/v1/accounting/ledger` - Add ledger entry
- `GET /api/v1/audit/logs` - Get audit logs
- `POST /api/v1/report/create` - Create a report
- `GET /api/v1/report/summary` - Financial summary

## Authentication

All endpoints (except registration) require an `api-key` header containing the user's API key.

## Environment Variables

- `DATABASE_URL` - Database connection string (defaults to SQLite `finance.db`)
- `SECRET_KEY` - Secret key for JWT tokens (defaults to `change_this_secret`)

## Dependencies

See `requirements.txt`. Key packages: fastapi, uvicorn, sqlalchemy, pydantic[email], psycopg2-binary, gunicorn.
