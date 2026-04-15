from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice
from app.models.tax import TaxRecord
from app.models.accounting import Ledger
from app.models.expense import Expense
from app.models.recurring_invoice import RecurringInvoice
from app.core.security import generate_api_key, hash_password, verify_password
from app.services.pdf_service import generate_invoice_pdf
from app.services.currency_service import (
    get_all_currencies, get_currency_symbol, convert_to_usd, format_amount
)

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£",
    "CAD": "CA$", "AUD": "A$", "JPY": "¥", "INR": "₹"
}


def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    return "evening"


def get_session_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_next_due_date(current: datetime, frequency: str) -> datetime:
    if frequency == "weekly":
        return current + timedelta(days=7)
    elif frequency == "monthly":
        return current + timedelta(days=30)
    elif frequency == "quarterly":
        return current + timedelta(days=91)
    return current + timedelta(days=30)


# ── Landing / Auth ────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def landing(request: Request, db: Session = Depends(get_db)):
    if get_session_user(request, db):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "landing.html")


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    if get_session_user(request, db):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if len(password) < 8:
        return templates.TemplateResponse(request, "register.html", {
            "error": "Password must be at least 8 characters."
        })
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(request, "register.html", {
            "error": "An account with this email already exists."
        })
    user = User(name=name, email=email, api_key=generate_api_key(),
                hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    return RedirectResponse("/login?registered=1", status_code=302)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, registered: str = None, db: Session = Depends(get_db)):
    if get_session_user(request, db):
        return RedirectResponse("/dashboard", status_code=302)
    success = "Account created! Please sign in." if registered else None
    return templates.TemplateResponse(request, "login.html", {"error": None, "success": success})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request, "login.html", {
            "error": "Invalid email or password.", "success": None
        })
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    invoices = db.query(Invoice).filter(Invoice.user_id == user.id).all()
    tax_records = db.query(TaxRecord).filter(TaxRecord.user_id == user.id).count()
    ledger_entries = db.query(Ledger).filter(Ledger.user_id == user.id).count()
    expenses = db.query(Expense).filter(Expense.user_id == user.id).all()

    total_revenue_usd = sum(convert_to_usd(i.total, i.currency or "USD") for i in invoices)
    total_expenses_usd = sum(convert_to_usd(e.amount, e.currency or "USD") for e in expenses)
    paid_invoices = sum(1 for i in invoices if i.status == "paid")

    stats = {
        "total_revenue": total_revenue_usd,
        "total_invoices": len(invoices),
        "paid_invoices": paid_invoices,
        "tax_records": tax_records,
        "ledger_entries": ledger_entries,
        "total_expenses": total_expenses_usd,
    }

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user, "stats": stats, "greeting": get_greeting(),
    })


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("/dashboard/invoices", response_class=HTMLResponse)
def invoices_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    invoices = db.query(Invoice).filter(Invoice.user_id == user.id).order_by(Invoice.id.desc()).all()
    return templates.TemplateResponse(request, "invoices.html", {
        "user": user, "invoices": invoices,
        "currencies": get_all_currencies(), "symbols": CURRENCY_SYMBOLS,
    })


@router.post("/dashboard/invoices", response_class=HTMLResponse)
def create_invoice(
    request: Request,
    customer_name: str = Form(...),
    customer_email: str = Form(None),
    amount: float = Form(...),
    tax: float = Form(...),
    currency: str = Form("USD"),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    total = amount + (amount * tax / 100)
    invoice = Invoice(user_id=user.id, customer_name=customer_name,
                      customer_email=customer_email, amount=amount,
                      tax=tax, total=total, currency=currency)
    db.add(invoice)
    db.commit()
    return RedirectResponse("/dashboard/invoices", status_code=302)


@router.get("/dashboard/invoices/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user.id).first()
    if not invoice:
        return RedirectResponse("/dashboard/invoices", status_code=302)
    pdf_bytes = generate_invoice_pdf(invoice, user)
    filename = f"invoice_{str(invoice.id).zfill(6)}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/dashboard/invoices/{invoice_id}/status")
def update_invoice_status(
    invoice_id: int, request: Request,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user.id).first()
    if invoice and status in ("paid", "cancelled", "overdue", "pending"):
        invoice.status = status
        db.commit()
    return RedirectResponse("/dashboard/invoices", status_code=302)


# ── Tax ───────────────────────────────────────────────────────────────────────

@router.get("/dashboard/tax", response_class=HTMLResponse)
def tax_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    records = db.query(TaxRecord).filter(TaxRecord.user_id == user.id).order_by(TaxRecord.id.desc()).all()
    return templates.TemplateResponse(request, "tax.html", {"user": user, "records": records, "result": None})


@router.post("/dashboard/tax", response_class=HTMLResponse)
def calculate_tax(
    request: Request,
    income: float = Form(...),
    tax_rate: float = Form(...),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    tax_amount = income * tax_rate / 100
    record = TaxRecord(user_id=user.id, income=income, tax_rate=tax_rate, tax_amount=tax_amount)
    db.add(record)
    db.commit()
    db.refresh(record)
    records = db.query(TaxRecord).filter(TaxRecord.user_id == user.id).order_by(TaxRecord.id.desc()).all()
    return templates.TemplateResponse(request, "tax.html", {"user": user, "records": records, "result": record})


# ── Accounting ────────────────────────────────────────────────────────────────

@router.get("/dashboard/accounting", response_class=HTMLResponse)
def accounting_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    entries = db.query(Ledger).filter(Ledger.user_id == user.id).order_by(Ledger.id.desc()).all()
    return templates.TemplateResponse(request, "accounting.html", {"user": user, "entries": entries})


@router.post("/dashboard/accounting", response_class=HTMLResponse)
def add_ledger(
    request: Request,
    entry_type: str = Form(...),
    amount: float = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    entry = Ledger(user_id=user.id, entry_type=entry_type, amount=amount, description=description)
    db.add(entry)
    db.commit()
    return RedirectResponse("/dashboard/accounting", status_code=302)


# ── Expenses ──────────────────────────────────────────────────────────────────

@router.get("/dashboard/expenses", response_class=HTMLResponse)
def expenses_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    expenses = db.query(Expense).filter(Expense.user_id == user.id).order_by(Expense.id.desc()).all()
    return templates.TemplateResponse(request, "expenses.html", {
        "user": user, "expenses": expenses,
        "currencies": get_all_currencies(), "symbols": CURRENCY_SYMBOLS,
    })


@router.post("/dashboard/expenses", response_class=HTMLResponse)
def add_expense(
    request: Request,
    title: str = Form(...),
    amount: float = Form(...),
    category: str = Form(...),
    currency: str = Form("USD"),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    expense = Expense(user_id=user.id, title=title, amount=amount,
                      category=category, currency=currency, notes=notes)
    db.add(expense)
    db.commit()
    return RedirectResponse("/dashboard/expenses", status_code=302)


@router.post("/dashboard/expenses/{expense_id}/delete")
def delete_expense(expense_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.user_id == user.id).first()
    if expense:
        db.delete(expense)
        db.commit()
    return RedirectResponse("/dashboard/expenses", status_code=302)


# ── Recurring Invoices ────────────────────────────────────────────────────────

@router.get("/dashboard/recurring", response_class=HTMLResponse)
def recurring_page(request: Request, db: Session = Depends(get_db), generated: int = None):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    recurring = db.query(RecurringInvoice).filter(RecurringInvoice.user_id == user.id).order_by(RecurringInvoice.id.desc()).all()
    due_count = sum(1 for r in recurring if r.is_active and r.next_due_date <= datetime.utcnow())
    return templates.TemplateResponse(request, "recurring.html", {
        "user": user, "recurring": recurring, "due_count": due_count,
        "currencies": get_all_currencies(), "symbols": CURRENCY_SYMBOLS,
        "generated": generated,
    })


@router.post("/dashboard/recurring")
def add_recurring(
    request: Request,
    customer_name: str = Form(...),
    customer_email: str = Form(None),
    amount: float = Form(...),
    tax: float = Form(...),
    currency: str = Form("USD"),
    frequency: str = Form(...),
    next_due_date: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    due_date = datetime.strptime(next_due_date, "%Y-%m-%d")
    rec = RecurringInvoice(
        user_id=user.id, customer_name=customer_name, customer_email=customer_email,
        amount=amount, tax=tax, currency=currency, frequency=frequency, next_due_date=due_date
    )
    db.add(rec)
    db.commit()
    return RedirectResponse("/dashboard/recurring", status_code=302)


@router.post("/dashboard/recurring/generate")
def generate_due_invoices(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    now = datetime.utcnow()
    due = db.query(RecurringInvoice).filter(
        RecurringInvoice.user_id == user.id,
        RecurringInvoice.is_active == True,
        RecurringInvoice.next_due_date <= now
    ).all()
    count = 0
    for r in due:
        total = r.amount + (r.amount * r.tax / 100)
        invoice = Invoice(user_id=user.id, customer_name=r.customer_name,
                          customer_email=r.customer_email, amount=r.amount,
                          tax=r.tax, total=total, currency=r.currency)
        db.add(invoice)
        r.next_due_date = get_next_due_date(r.next_due_date, r.frequency)
        count += 1
    db.commit()
    return RedirectResponse(f"/dashboard/recurring?generated={count}", status_code=302)


@router.post("/dashboard/recurring/{recurring_id}/toggle")
def toggle_recurring(recurring_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    rec = db.query(RecurringInvoice).filter(
        RecurringInvoice.id == recurring_id, RecurringInvoice.user_id == user.id
    ).first()
    if rec:
        rec.is_active = not rec.is_active
        db.commit()
    return RedirectResponse("/dashboard/recurring", status_code=302)


@router.post("/dashboard/recurring/{recurring_id}/delete")
def delete_recurring(recurring_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    rec = db.query(RecurringInvoice).filter(
        RecurringInvoice.id == recurring_id, RecurringInvoice.user_id == user.id
    ).first()
    if rec:
        db.delete(rec)
        db.commit()
    return RedirectResponse("/dashboard/recurring", status_code=302)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/dashboard/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    invoices = db.query(Invoice).filter(Invoice.user_id == user.id).all()
    total_revenue = sum(convert_to_usd(i.total, i.currency or "USD") for i in invoices)
    paid = sum(1 for i in invoices if i.status == "paid")
    pending = sum(1 for i in invoices if i.status == "pending")
    overdue = sum(1 for i in invoices if i.status == "overdue")
    tax_records = db.query(TaxRecord).filter(TaxRecord.user_id == user.id).all()
    total_tax = sum(r.tax_amount for r in tax_records)
    expenses = db.query(Expense).filter(Expense.user_id == user.id).all()
    total_expenses = sum(convert_to_usd(e.amount, e.currency or "USD") for e in expenses)
    return templates.TemplateResponse(request, "reports.html", {
        "user": user, "total_revenue": total_revenue, "paid": paid,
        "pending": pending, "overdue": overdue, "total_invoices": len(invoices),
        "total_tax": total_tax, "tax_records": len(tax_records),
        "total_expenses": total_expenses,
    })


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/dashboard/audit", response_class=HTMLResponse)
def audit_page(request: Request, db: Session = Depends(get_db)):
    from app.models.audit import AuditLog
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    logs = db.query(AuditLog).filter(AuditLog.user_id == user.id).order_by(AuditLog.id.desc()).all()
    return templates.TemplateResponse(request, "audit.html", {"user": user, "logs": logs})
