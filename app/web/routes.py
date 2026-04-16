import base64
import io
import os
import secrets
from datetime import datetime, timedelta

import pyotp
import qrcode
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
from app.models.organization import Organization
from app.models.invite import Invite
from app.core.security import generate_api_key, hash_password, verify_password
from app.services.pdf_service import generate_invoice_pdf
from app.services.currency_service import get_all_currencies, convert_to_usd
from app.services.email_service import (
    is_email_configured, send_password_reset_email, send_invite_email
)

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£",
    "CAD": "CA$", "AUD": "A$", "JPY": "¥", "INR": "₹"
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_base_url() -> str:
    domain = os.getenv("REPLIT_DEV_DOMAIN", "")
    return f"https://{domain}" if domain else os.getenv("APP_URL", "http://localhost:5000")


def get_greeting():
    h = datetime.now().hour
    return "morning" if h < 12 else ("afternoon" if h < 17 else "evening")


def get_session_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_org_user_ids(user: User, db: Session) -> list:
    org_id = getattr(user, "org_id", None)
    if org_id:
        return [row[0] for row in db.query(User.id).filter(User.org_id == org_id).all()]
    return [user.id]


def get_org_name(user: User, db: Session) -> str:
    org_id = getattr(user, "org_id", None)
    if org_id:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org:
            return org.name
    return f"{user.name}'s Organization"


def can_write(user: User) -> bool:
    return (getattr(user, "role", "admin") or "admin") in ("admin", "accountant")


def is_admin(user: User) -> bool:
    return (getattr(user, "role", "admin") or "admin") == "admin"


def make_qr_base64(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def get_next_due_date(current: datetime, frequency: str) -> datetime:
    if frequency == "weekly":
        return current + timedelta(days=7)
    elif frequency == "monthly":
        return current + timedelta(days=30)
    return current + timedelta(days=91)


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
        return templates.TemplateResponse(request, "register.html",
                                          {"error": "Password must be at least 8 characters."})
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(request, "register.html",
                                          {"error": "An account with this email already exists."})
    # Create personal org for new user
    org = Organization(name=f"{name}'s Organization")
    db.add(org)
    db.flush()
    user = User(name=name, email=email, api_key=generate_api_key(),
                hashed_password=hash_password(password), role="admin", org_id=org.id)
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
        return templates.TemplateResponse(request, "login.html",
                                          {"error": "Invalid email or password.", "success": None})
    if getattr(user, "is_2fa_enabled", False):
        request.session["pending_2fa_user_id"] = user.id
        return RedirectResponse("/verify-otp", status_code=302)
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


# ── Forgot / Reset Password ───────────────────────────────────────────────────

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html",
                                      {"error": None, "success": None, "reset_link": None})


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    reset_link = None
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        url = f"{get_base_url()}/reset-password/{token}"
        sent = send_password_reset_email(email, url)
        if not sent:
            reset_link = url  # show link in dev mode
    return templates.TemplateResponse(request, "forgot_password.html", {
        "success": "If that email exists, a reset link has been sent." if not reset_link else None,
        "reset_link": reset_link,
        "error": None,
    })


@router.get("/reset-password/{token}", response_class=HTMLResponse)
def reset_password_page(token: str, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    valid = user and user.reset_token_expires and user.reset_token_expires > datetime.utcnow()
    return templates.TemplateResponse(request, "reset_password.html",
                                      {"invalid": not valid, "error": None, "token": token})


@router.post("/reset-password/{token}", response_class=HTMLResponse)
def reset_password_submit(
    token: str, request: Request,
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.reset_token == token).first()
    valid = user and user.reset_token_expires and user.reset_token_expires > datetime.utcnow()
    if not valid:
        return templates.TemplateResponse(request, "reset_password.html",
                                          {"invalid": True, "error": None})
    if password != confirm_password:
        return templates.TemplateResponse(request, "reset_password.html",
                                          {"invalid": False, "error": "Passwords do not match."})
    if len(password) < 8:
        return templates.TemplateResponse(request, "reset_password.html",
                                          {"invalid": False, "error": "Password must be at least 8 characters."})
    user.hashed_password = hash_password(password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return RedirectResponse("/login?registered=1", status_code=302)


# ── Two-Factor Auth ───────────────────────────────────────────────────────────

@router.get("/verify-otp", response_class=HTMLResponse)
def verify_otp_page(request: Request):
    if not request.session.get("pending_2fa_user_id"):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "verify_otp.html", {"error": None})


@router.post("/verify-otp", response_class=HTMLResponse)
def verify_otp_submit(
    request: Request,
    otp_code: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.session.get("pending_2fa_user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse("/login", status_code=302)
    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(otp_code.strip(), valid_window=1):
        request.session["user_id"] = user.id
        request.session.pop("pending_2fa_user_id", None)
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "verify_otp.html",
                                      {"error": "Invalid code. Please try again."})


# ── Accept Invite ─────────────────────────────────────────────────────────────

@router.get("/accept-invite/{token}", response_class=HTMLResponse)
def accept_invite_page(token: str, request: Request, db: Session = Depends(get_db)):
    invite = db.query(Invite).filter(Invite.token == token, Invite.used == False).first()
    if not invite or invite.expires_at < datetime.utcnow():
        return templates.TemplateResponse(request, "accept_invite.html",
                                          {"invalid": True, "org_name": "", "role": "", "invite_email": ""})
    org = db.query(Organization).filter(Organization.id == invite.org_id).first()
    return templates.TemplateResponse(request, "accept_invite.html", {
        "invalid": False, "org_name": org.name if org else "",
        "role": invite.role, "invite_email": invite.email, "error": None,
    })


@router.post("/accept-invite/{token}", response_class=HTMLResponse)
def accept_invite_submit(
    token: str, request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    invite = db.query(Invite).filter(Invite.token == token, Invite.used == False).first()
    if not invite or invite.expires_at < datetime.utcnow():
        return RedirectResponse("/login", status_code=302)
    if len(password) < 8:
        org = db.query(Organization).filter(Organization.id == invite.org_id).first()
        return templates.TemplateResponse(request, "accept_invite.html", {
            "invalid": False, "org_name": org.name if org else "",
            "role": invite.role, "invite_email": invite.email,
            "error": "Password must be at least 8 characters.",
        })
    user = User(name=name, email=invite.email, api_key=generate_api_key(),
                hashed_password=hash_password(password),
                org_id=invite.org_id, role=invite.role)
    db.add(user)
    invite.used = True
    db.commit()
    return RedirectResponse("/login?registered=1", status_code=302)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    uid_list = get_org_user_ids(user, db)
    invoices = db.query(Invoice).filter(Invoice.user_id.in_(uid_list)).all()
    tax_records = db.query(TaxRecord).filter(TaxRecord.user_id.in_(uid_list)).count()
    ledger_entries = db.query(Ledger).filter(Ledger.user_id.in_(uid_list)).count()
    expenses = db.query(Expense).filter(Expense.user_id.in_(uid_list)).all()
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


# ── Profile & Security ────────────────────────────────────────────────────────

@router.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    success: str = None,
    error: str = None,
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    qr_code = None
    totp_secret = None
    pending = request.session.get("totp_setup_secret")
    if pending:
        totp = pyotp.TOTP(pending)
        uri = totp.provisioning_uri(name=user.email, issuer_name="FinanceAPI")
        qr_code = make_qr_base64(uri)
        totp_secret = pending
    success_map = {
        "2fa_enabled": "Two-factor authentication has been enabled.",
        "2fa_disabled": "Two-factor authentication has been disabled.",
        "password_changed": "Password updated successfully.",
    }
    return templates.TemplateResponse(request, "profile.html", {
        "user": user,
        "org_name": get_org_name(user, db),
        "qr_code": qr_code,
        "totp_secret": totp_secret,
        "success": success_map.get(success, success),
        "error": error,
    })


@router.post("/profile/2fa/setup")
def setup_2fa(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    secret = pyotp.random_base32()
    request.session["totp_setup_secret"] = secret
    return RedirectResponse("/profile", status_code=302)


@router.post("/profile/2fa/enable", response_class=HTMLResponse)
def enable_2fa(
    request: Request,
    otp_code: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    secret = request.session.get("totp_setup_secret")
    if not secret:
        return RedirectResponse("/profile", status_code=302)
    totp = pyotp.TOTP(secret)
    if totp.verify(otp_code.strip(), valid_window=1):
        user.totp_secret = secret
        user.is_2fa_enabled = True
        db.commit()
        request.session.pop("totp_setup_secret", None)
        return RedirectResponse("/profile?success=2fa_enabled", status_code=302)
    # Regenerate QR for error state
    t = pyotp.TOTP(secret)
    uri = t.provisioning_uri(name=user.email, issuer_name="FinanceAPI")
    qr_code = make_qr_base64(uri)
    return templates.TemplateResponse(request, "profile.html", {
        "user": user, "org_name": get_org_name(user, db),
        "qr_code": qr_code, "totp_secret": secret,
        "error": "Invalid code. Please try again.", "success": None,
    })


@router.post("/profile/2fa/disable")
def disable_2fa(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    user.totp_secret = None
    user.is_2fa_enabled = False
    db.commit()
    return RedirectResponse("/profile?success=2fa_disabled", status_code=302)


@router.post("/profile/change-password", response_class=HTMLResponse)
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not verify_password(current_password, user.hashed_password or ""):
        return RedirectResponse("/profile?error=wrong_password", status_code=302)
    if new_password != confirm_password:
        return RedirectResponse("/profile?error=passwords_mismatch", status_code=302)
    if len(new_password) < 8:
        return RedirectResponse("/profile?error=password_short", status_code=302)
    user.hashed_password = hash_password(new_password)
    db.commit()
    return RedirectResponse("/profile?success=password_changed", status_code=302)


# ── Team Management ───────────────────────────────────────────────────────────

@router.get("/dashboard/team", response_class=HTMLResponse)
def team_page(
    request: Request,
    success: str = None,
    invite_link: str = None,
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not is_admin(user):
        return RedirectResponse("/dashboard", status_code=302)
    org_id = getattr(user, "org_id", None)
    members = db.query(User).filter(User.org_id == org_id).all() if org_id else [user]
    pending_invites = (
        db.query(Invite).filter(
            Invite.org_id == org_id,
            Invite.used == False,
            Invite.expires_at > datetime.utcnow()
        ).all() if org_id else []
    )
    return templates.TemplateResponse(request, "team.html", {
        "user": user,
        "org_name": get_org_name(user, db),
        "members": members,
        "pending_invites": pending_invites,
        "success": success,
        "invite_link": invite_link,
    })


@router.post("/dashboard/team/invite")
def invite_member(
    request: Request,
    email: str = Form(...),
    role: str = Form("viewer"),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user or not is_admin(user):
        return RedirectResponse("/dashboard", status_code=302)
    org_id = getattr(user, "org_id", None)
    if not org_id:
        return RedirectResponse("/dashboard/team", status_code=302)
    token = secrets.token_urlsafe(32)
    invite = Invite(
        org_id=org_id, email=email, role=role, token=token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(invite)
    db.commit()
    invite_url = f"{get_base_url()}/accept-invite/{token}"
    sent = send_invite_email(email, invite_url, get_org_name(user, db), role)
    link = None if sent else invite_url
    msg = f"Invitation sent to {email}." if sent else f"Invite created for {email}."
    return RedirectResponse(
        f"/dashboard/team?success={msg}&invite_link={link or ''}",
        status_code=302
    )


@router.post("/dashboard/team/{member_id}/role")
def update_member_role(
    member_id: int, request: Request,
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user or not is_admin(user):
        return RedirectResponse("/dashboard", status_code=302)
    member = db.query(User).filter(
        User.id == member_id, User.org_id == user.org_id
    ).first()
    if member and role in ("admin", "accountant", "viewer"):
        member.role = role
        db.commit()
    return RedirectResponse("/dashboard/team?success=Role+updated.", status_code=302)


@router.post("/dashboard/team/{member_id}/remove")
def remove_member(member_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user or not is_admin(user):
        return RedirectResponse("/dashboard", status_code=302)
    member = db.query(User).filter(
        User.id == member_id, User.org_id == user.org_id
    ).first()
    if member and member.id != user.id:
        member.org_id = None
        db.commit()
    return RedirectResponse("/dashboard/team?success=Member+removed.", status_code=302)


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("/dashboard/invoices", response_class=HTMLResponse)
def invoices_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    uid_list = get_org_user_ids(user, db)
    invoices = db.query(Invoice).filter(Invoice.user_id.in_(uid_list)).order_by(Invoice.id.desc()).all()
    return templates.TemplateResponse(request, "invoices.html", {
        "user": user, "invoices": invoices,
        "currencies": get_all_currencies(), "symbols": CURRENCY_SYMBOLS,
    })


@router.post("/dashboard/invoices")
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
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/invoices", status_code=302)
    total = amount + (amount * tax / 100)
    inv = Invoice(user_id=user.id, customer_name=customer_name, customer_email=customer_email,
                  amount=amount, tax=tax, total=total, currency=currency)
    db.add(inv)
    db.commit()
    return RedirectResponse("/dashboard/invoices", status_code=302)


@router.get("/dashboard/invoices/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    uid_list = get_org_user_ids(user, db)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id.in_(uid_list)).first()
    if not invoice:
        return RedirectResponse("/dashboard/invoices", status_code=302)
    pdf_bytes = generate_invoice_pdf(invoice, user)
    filename = f"invoice_{str(invoice.id).zfill(6)}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/dashboard/invoices/{invoice_id}/status")
def update_invoice_status(
    invoice_id: int, request: Request,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/invoices", status_code=302)
    uid_list = get_org_user_ids(user, db)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id.in_(uid_list)).first()
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
    uid_list = get_org_user_ids(user, db)
    records = db.query(TaxRecord).filter(TaxRecord.user_id.in_(uid_list)).order_by(TaxRecord.id.desc()).all()
    return templates.TemplateResponse(request, "tax.html", {"user": user, "records": records, "result": None})


@router.post("/dashboard/tax", response_class=HTMLResponse)
def calculate_tax(
    request: Request,
    income: float = Form(...),
    tax_rate: float = Form(...),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/tax", status_code=302)
    tax_amount = income * tax_rate / 100
    record = TaxRecord(user_id=user.id, income=income, tax_rate=tax_rate, tax_amount=tax_amount)
    db.add(record)
    db.commit()
    db.refresh(record)
    uid_list = get_org_user_ids(user, db)
    records = db.query(TaxRecord).filter(TaxRecord.user_id.in_(uid_list)).order_by(TaxRecord.id.desc()).all()
    return templates.TemplateResponse(request, "tax.html", {"user": user, "records": records, "result": record})


# ── Accounting ────────────────────────────────────────────────────────────────

@router.get("/dashboard/accounting", response_class=HTMLResponse)
def accounting_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    uid_list = get_org_user_ids(user, db)
    entries = db.query(Ledger).filter(Ledger.user_id.in_(uid_list)).order_by(Ledger.id.desc()).all()
    return templates.TemplateResponse(request, "accounting.html", {"user": user, "entries": entries})


@router.post("/dashboard/accounting")
def add_ledger(
    request: Request,
    entry_type: str = Form(...),
    amount: float = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_session_user(request, db)
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/accounting", status_code=302)
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
    uid_list = get_org_user_ids(user, db)
    expenses = db.query(Expense).filter(Expense.user_id.in_(uid_list)).order_by(Expense.id.desc()).all()
    return templates.TemplateResponse(request, "expenses.html", {
        "user": user, "expenses": expenses,
        "currencies": get_all_currencies(), "symbols": CURRENCY_SYMBOLS,
    })


@router.post("/dashboard/expenses")
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
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/expenses", status_code=302)
    expense = Expense(user_id=user.id, title=title, amount=amount,
                      category=category, currency=currency, notes=notes)
    db.add(expense)
    db.commit()
    return RedirectResponse("/dashboard/expenses", status_code=302)


@router.post("/dashboard/expenses/{expense_id}/delete")
def delete_expense(expense_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/expenses", status_code=302)
    uid_list = get_org_user_ids(user, db)
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.user_id.in_(uid_list)).first()
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
    uid_list = get_org_user_ids(user, db)
    recurring = db.query(RecurringInvoice).filter(
        RecurringInvoice.user_id.in_(uid_list)
    ).order_by(RecurringInvoice.id.desc()).all()
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
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/recurring", status_code=302)
    due_date = datetime.strptime(next_due_date, "%Y-%m-%d")
    rec = RecurringInvoice(user_id=user.id, customer_name=customer_name, customer_email=customer_email,
                           amount=amount, tax=tax, currency=currency, frequency=frequency,
                           next_due_date=due_date)
    db.add(rec)
    db.commit()
    return RedirectResponse("/dashboard/recurring", status_code=302)


@router.post("/dashboard/recurring/generate")
def generate_due_invoices(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/recurring", status_code=302)
    uid_list = get_org_user_ids(user, db)
    due = db.query(RecurringInvoice).filter(
        RecurringInvoice.user_id.in_(uid_list),
        RecurringInvoice.is_active == True,
        RecurringInvoice.next_due_date <= datetime.utcnow()
    ).all()
    count = 0
    for r in due:
        total = r.amount + (r.amount * r.tax / 100)
        inv = Invoice(user_id=r.user_id, customer_name=r.customer_name,
                      customer_email=r.customer_email, amount=r.amount,
                      tax=r.tax, total=total, currency=r.currency)
        db.add(inv)
        r.next_due_date = get_next_due_date(r.next_due_date, r.frequency)
        count += 1
    db.commit()
    return RedirectResponse(f"/dashboard/recurring?generated={count}", status_code=302)


@router.post("/dashboard/recurring/{recurring_id}/toggle")
def toggle_recurring(recurring_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/recurring", status_code=302)
    uid_list = get_org_user_ids(user, db)
    rec = db.query(RecurringInvoice).filter(
        RecurringInvoice.id == recurring_id, RecurringInvoice.user_id.in_(uid_list)
    ).first()
    if rec:
        rec.is_active = not rec.is_active
        db.commit()
    return RedirectResponse("/dashboard/recurring", status_code=302)


@router.post("/dashboard/recurring/{recurring_id}/delete")
def delete_recurring(recurring_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user or not can_write(user):
        return RedirectResponse("/dashboard/recurring", status_code=302)
    uid_list = get_org_user_ids(user, db)
    rec = db.query(RecurringInvoice).filter(
        RecurringInvoice.id == recurring_id, RecurringInvoice.user_id.in_(uid_list)
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
    uid_list = get_org_user_ids(user, db)
    invoices = db.query(Invoice).filter(Invoice.user_id.in_(uid_list)).all()
    total_revenue = sum(convert_to_usd(i.total, i.currency or "USD") for i in invoices)
    paid = sum(1 for i in invoices if i.status == "paid")
    pending = sum(1 for i in invoices if i.status == "pending")
    overdue = sum(1 for i in invoices if i.status == "overdue")
    tax_records = db.query(TaxRecord).filter(TaxRecord.user_id.in_(uid_list)).all()
    total_tax = sum(r.tax_amount for r in tax_records)
    expenses = db.query(Expense).filter(Expense.user_id.in_(uid_list)).all()
    total_expenses = sum(convert_to_usd(e.amount, e.currency or "USD") for e in expenses)
    return templates.TemplateResponse(request, "reports.html", {
        "user": user, "total_revenue": total_revenue, "paid": paid,
        "pending": pending, "overdue": overdue, "total_invoices": len(invoices),
        "total_tax": total_tax, "tax_records": len(tax_records), "total_expenses": total_expenses,
    })


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/dashboard/audit", response_class=HTMLResponse)
def audit_page(request: Request, db: Session = Depends(get_db)):
    from app.models.audit import AuditLog
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    uid_list = get_org_user_ids(user, db)
    logs = db.query(AuditLog).filter(AuditLog.user_id.in_(uid_list)).order_by(AuditLog.id.desc()).all()
    return templates.TemplateResponse(request, "audit.html", {"user": user, "logs": logs})
