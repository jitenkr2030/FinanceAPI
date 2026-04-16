from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.routes.router import api_router
from app.web.routes import router as web_router

# Import all models so create_all picks them up
import app.models.user              # noqa: F401
import app.models.invoice           # noqa: F401
import app.models.tax               # noqa: F401
import app.models.accounting        # noqa: F401
import app.models.audit             # noqa: F401
import app.models.report            # noqa: F401
import app.models.expense           # noqa: F401
import app.models.recurring_invoice # noqa: F401
import app.models.organization      # noqa: F401
import app.models.invite            # noqa: F401

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Create all tables (new tables only; existing tables are not modified)
Base.metadata.create_all(bind=engine)

# ── Column migrations (each in its own connection so one failure won't block the rest) ──
COLUMN_MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN hashed_password VARCHAR",
    "ALTER TABLE users ADD COLUMN org_id INTEGER REFERENCES organizations(id)",
    "ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'admin'",
    "ALTER TABLE users ADD COLUMN reset_token VARCHAR",
    "ALTER TABLE users ADD COLUMN reset_token_expires TIMESTAMP",
    "ALTER TABLE users ADD COLUMN totp_secret VARCHAR",
    "ALTER TABLE users ADD COLUMN is_2fa_enabled BOOLEAN DEFAULT FALSE",
    "ALTER TABLE invoices ADD COLUMN currency VARCHAR DEFAULT 'USD'",
    "ALTER TABLE invoices ADD COLUMN status VARCHAR DEFAULT 'pending'",
]
for _stmt in COLUMN_MIGRATIONS:
    try:
        with engine.connect() as _conn:
            _conn.execute(text(_stmt))
            _conn.commit()
    except Exception:
        pass

# ── Seed: create an Organization for existing users who don't have one ──────────
try:
    from app.models.user import User
    from app.models.organization import Organization

    with SessionLocal() as db:
        users_without_org = db.query(User).filter(User.org_id == None).all()
        for u in users_without_org:
            org = Organization(name=f"{u.name}'s Organization")
            db.add(org)
            db.flush()
            u.org_id = org.id
            if not u.role:
                u.role = "admin"
        if users_without_org:
            db.commit()
except Exception:
    pass

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web_router)
app.include_router(api_router, prefix=settings.API_V1_STR)
