from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice
from app.models.tax import TaxRecord
from app.models.accounting import Ledger
from app.core.security import generate_api_key, hash_password, verify_password

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


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


@router.get("/", response_class=HTMLResponse)
def landing(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "landing.html")


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if user:
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

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse(request, "register.html", {
            "error": "An account with this email already exists."
        })

    api_key = generate_api_key()
    user = User(
        name=name,
        email=email,
        api_key=api_key,
        hashed_password=hash_password(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RedirectResponse("/login?registered=1", status_code=302)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, registered: str = None, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if user:
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
            "error": "Invalid email or password.",
            "success": None
        })

    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    invoices = db.query(Invoice).filter(Invoice.user_id == user.id).all()
    tax_records = db.query(TaxRecord).filter(TaxRecord.user_id == user.id).count()
    ledger_entries = db.query(Ledger).filter(Ledger.user_id == user.id).count()

    total_revenue = sum(i.total for i in invoices)
    paid_invoices = sum(1 for i in invoices if i.status == "paid")

    stats = {
        "total_revenue": total_revenue,
        "total_invoices": len(invoices),
        "paid_invoices": paid_invoices,
        "tax_records": tax_records,
        "ledger_entries": ledger_entries,
    }

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "stats": stats,
        "greeting": get_greeting(),
    })


@router.get("/dashboard/invoices", response_class=HTMLResponse)
def invoices_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    invoices = db.query(Invoice).filter(Invoice.user_id == user.id).order_by(Invoice.id.desc()).all()
    return templates.TemplateResponse(request, "invoices.html", {"user": user, "invoices": invoices})


@router.post("/dashboard/invoices", response_class=HTMLResponse)
def create_invoice(
    request: Request,
    customer_name: str = Form(...),
    customer_email: str = Form(None),
    amount: float = Form(...),
    tax: float = Form(...),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    total = amount + (amount * tax / 100)
    invoice = Invoice(
        user_id=user.id,
        customer_name=customer_name,
        customer_email=customer_email,
        amount=amount,
        tax=tax,
        total=total
    )
    db.add(invoice)
    db.commit()
    return RedirectResponse("/dashboard/invoices", status_code=302)


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


@router.get("/dashboard/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    invoices = db.query(Invoice).filter(Invoice.user_id == user.id).all()
    total_revenue = sum(i.total for i in invoices)
    paid = sum(1 for i in invoices if i.status == "paid")
    pending = sum(1 for i in invoices if i.status == "pending")
    tax_records = db.query(TaxRecord).filter(TaxRecord.user_id == user.id).all()
    total_tax = sum(r.tax_amount for r in tax_records)
    return templates.TemplateResponse(request, "reports.html", {
        "user": user,
        "total_revenue": total_revenue,
        "paid": paid,
        "pending": pending,
        "total_invoices": len(invoices),
        "total_tax": total_tax,
        "tax_records": len(tax_records)
    })


@router.get("/dashboard/audit", response_class=HTMLResponse)
def audit_page(request: Request, db: Session = Depends(get_db)):
    from app.models.audit import AuditLog
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    logs = db.query(AuditLog).filter(AuditLog.user_id == user.id).order_by(AuditLog.id.desc()).all()
    return templates.TemplateResponse(request, "audit.html", {"user": user, "logs": logs})
