# FinanceAPI — Smart Finance Management Platform

A full-stack Finance SaaS platform built with **FastAPI** and **Python**. Manage invoices, accounting ledgers, tax calculations, financial reports, and audit logs — all through a clean web interface and a powerful REST API.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Usage Guide](#usage-guide)
- [REST API Reference](#rest-api-reference)
- [Test Credentials](#test-credentials)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)

---

## Features

| Feature | Description |
|---|---|
| **User Authentication** | Register and log in with email & password. Session-based auth with secure cookie storage. |
| **Invoicing** | Create invoices with automatic tax calculation. Track customer name, email, amount, and status. |
| **Tax Calculator** | Calculate tax obligations based on income and tax rate. Full history of all calculations. |
| **Accounting Ledger** | Double-entry ledger to track credits and debits with descriptions. |
| **Financial Reports** | Auto-generated summaries of revenue, invoice status, and tax obligations. |
| **Audit Logs** | Full activity trail for every action performed in your account. |
| **REST API** | Complete API access via API key for integrating with any external tool or service. |
| **Interactive Docs** | Auto-generated Swagger UI at `/docs` for exploring and testing the API. |

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI
- **Database:** PostgreSQL (SQLAlchemy ORM)
- **Auth:** Session middleware (itsdangerous), bcrypt password hashing
- **Templating:** Jinja2 with Tailwind CSS
- **Server (dev):** Uvicorn with hot-reload
- **Server (prod):** Gunicorn + Uvicorn workers

---

## Project Structure

```
├── app/
│   ├── main.py                  # App entry point — middleware, routers, DB init
│   ├── core/
│   │   ├── config.py            # App settings and environment variables
│   │   ├── deps.py              # FastAPI dependencies (API key auth)
│   │   ├── security.py          # Password hashing and API key generation
│   │   ├── exceptions.py        # Custom exception handlers
│   │   ├── logging.py           # Logging configuration
│   │   └── middleware.py        # Custom middleware
│   ├── db/
│   │   ├── base.py              # SQLAlchemy declarative base
│   │   └── session.py           # Database engine and session factory
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── invoice.py
│   │   ├── tax.py
│   │   ├── accounting.py
│   │   ├── audit.py
│   │   └── report.py
│   ├── schemas/                 # Pydantic v2 request/response schemas
│   │   ├── user.py
│   │   ├── invoice.py
│   │   ├── tax.py
│   │   ├── accounting.py
│   │   ├── audit.py
│   │   └── report.py
│   ├── routes/
│   │   └── v1/                  # Versioned REST API endpoints
│   │       ├── auth.py
│   │       ├── invoice.py
│   │       ├── tax.py
│   │       ├── accounting.py
│   │       ├── audit.py
│   │       └── report.py
│   ├── services/                # Business logic layer
│   │   ├── auth_service.py
│   │   ├── invoice_service.py
│   │   ├── tax_service.py
│   │   ├── accounting_service.py
│   │   ├── audit_service.py
│   │   ├── report_service.py
│   │   └── analytics_service.py
│   ├── web/
│   │   └── routes.py            # Web UI routes (landing, login, register, dashboard)
│   ├── templates/               # Jinja2 HTML templates
│   │   ├── landing.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── invoices.html
│   │   ├── tax.html
│   │   ├── accounting.html
│   │   ├── reports.html
│   │   ├── audit.html
│   │   └── sidebar.html
│   └── static/                  # Static assets (CSS, JS)
├── requirements.txt
├── alembic.ini                  # Database migration config
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL (or SQLite for local development)
- `pip` package manager

### Step 1 — Clone the repository

```bash
git clone https://github.com/jitenkr2030/FinanceAPI.git
cd FinanceAPI
```

### Step 2 — Create a virtual environment

```bash
python -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

Create a `.env` file in the root directory (or export variables directly):

```env
DATABASE_URL=postgresql://user:password@localhost/financedb
SECRET_KEY=your-super-secret-key-change-this
```

> For local development without PostgreSQL, the app defaults to SQLite (`finance.db`) automatically.

### Step 5 — Run the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

Open your browser at **http://localhost:5000**

---

## Running the Application

### Development mode (with auto-reload)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

### Production mode (with Gunicorn)

```bash
gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 2 app.main:app
```

---

## Usage Guide

### 1. Landing Page

Visit the root URL (`/`) to see the landing page. From here you can:
- Click **Get started free** to create an account
- Click **Log in** to sign in to an existing account

### 2. Register an Account

Go to `/register` and fill in:
- **Full name**
- **Email address**
- **Password** (minimum 8 characters)

After registering, you will be redirected to the login page.

### 3. Log In

Go to `/login`, enter your email and password. On success you will land on the **Dashboard**.

### 4. Dashboard

The dashboard gives you an at-a-glance overview of:
- Total revenue from all invoices
- Number of invoices (and how many are paid)
- Tax records count
- Ledger entries count
- Your unique **API Key** for REST API access

### 5. Invoices (`/dashboard/invoices`)

- Click **New Invoice** to open the creation form
- Fill in customer name, email (optional), amount, and tax rate (%)
- The total is calculated automatically: `total = amount + (amount × tax / 100)`
- All invoices are listed in a table with status badges (Pending / Paid / Cancelled)

### 6. Tax Calculator (`/dashboard/tax`)

- Enter an income amount and tax rate percentage
- Click **Calculate** to instantly compute the tax amount
- Every calculation is saved to your history table

### 7. Accounting Ledger (`/dashboard/accounting`)

- Click **Add Entry** to record a credit or debit
- Fill in the entry type, amount, and an optional description
- The page shows a running summary of total credits vs. total debits

### 8. Financial Reports (`/dashboard/reports`)

Auto-generated report showing:
- Gross Revenue
- Total Tax Obligations
- Net Revenue (after tax)
- Invoice collection rate (% of invoices paid)

### 9. Audit Logs (`/dashboard/audit`)

Read-only log of all actions recorded for your account via the API.

### 10. Sign Out

Click **Sign out** in the bottom of the sidebar to end your session.

---

## REST API Reference

All API endpoints are under `/api/v1`. Authentication uses an **API Key** passed as a request header:

```
api-key: your-api-key-here
```

Your API key is displayed on the Dashboard after logging in.

### Auth

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Register a new user | No |

**Request body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com"
}
```

### Invoices

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/invoice/create` | Create an invoice |

**Request body:**
```json
{
  "customer_name": "Acme Corp",
  "customer_email": "billing@acme.com",
  "amount": 1000.00,
  "tax": 10
}
```

### Tax

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/tax/calculate` | Calculate and record tax |

**Request body:**
```json
{
  "income": 50000.00,
  "tax_rate": 20
}
```

### Accounting

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/accounting/entry` | Add a ledger entry |

**Request body:**
```json
{
  "entry_type": "credit",
  "amount": 5000.00,
  "description": "Client payment received"
}
```

### Audit

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/audit/log` | Log an audit action |

### Reports

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/report/create` | Create a report record |
| GET | `/api/v1/report/summary` | Get financial summary |

### Interactive API Docs

Visit `/docs` in your browser for the full interactive Swagger UI where you can test all endpoints directly.

---

## Test Credentials

Use these pre-created accounts to explore the platform:

| Role | Email | Password | API Key |
|---|---|---|---|
| Admin | `admin@financeapi.com` | `Admin@1234` | `3f9cf7868eb9f24fc9e2a14afec2fca5` |
| User | `user@financeapi.com` | `User@1234` | `628bebe8de04f52bcc0092168f5bb2c0` |

---

## Deployment

The app is deployed on **Replit** and publicly accessible at:

**https://finance-api--JitenderKumar33.replit.app**

For self-hosting, use the production Gunicorn command:

```bash
gunicorn -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  app.main:app
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///./finance.db` |
| `SECRET_KEY` | Secret key for session signing | `change_this_secret` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session/token expiry in minutes | `1440` (1 day) |

> **Important:** Always set a strong, random `SECRET_KEY` in production. Never use the default value.

---

## License

This project is open source and available under the [MIT License](LICENSE).
