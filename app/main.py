from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.routes.router import api_router
from app.web.routes import router as web_router

# Import all models so create_all picks them up
import app.models.user          # noqa: F401
import app.models.invoice       # noqa: F401
import app.models.tax           # noqa: F401
import app.models.accounting    # noqa: F401
import app.models.audit         # noqa: F401
import app.models.report        # noqa: F401
import app.models.expense       # noqa: F401
import app.models.recurring_invoice  # noqa: F401

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

Base.metadata.create_all(bind=engine)

# Run incremental migrations safely — each in its own connection/transaction
# so a failure (e.g. column already exists) does not abort subsequent statements.
MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN hashed_password VARCHAR",
    "ALTER TABLE invoices ADD COLUMN currency VARCHAR DEFAULT 'USD'",
    "ALTER TABLE invoices ADD COLUMN status VARCHAR DEFAULT 'pending'",
]
for _stmt in MIGRATIONS:
    try:
        with engine.connect() as _conn:
            _conn.execute(text(_stmt))
            _conn.commit()
    except Exception:
        pass

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(web_router)
app.include_router(api_router, prefix=settings.API_V1_STR)
