from fastapi import APIRouter

from app.routes.v1 import invoice, tax, audit, accounting, report, auth

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(invoice.router)
api_router.include_router(tax.router)
api_router.include_router(accounting.router)
api_router.include_router(audit.router)
api_router.include_router(report.router)
