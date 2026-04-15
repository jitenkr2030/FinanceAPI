from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services.invoice_service import create_invoice

router = APIRouter(prefix="/invoice", tags=["Invoice"])


@router.post("/create", response_model=InvoiceResponse)
def create_invoice_api(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    invoice = create_invoice(db, current_user.id, data)
    return invoice
