from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.schemas.accounting import LedgerCreate, LedgerResponse
from app.services.accounting_service import add_ledger_entry

router = APIRouter(prefix="/accounting", tags=["Accounting"])


@router.post("/entry", response_model=LedgerResponse)
def add_entry_api(
    data: LedgerCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    entry = add_ledger_entry(db, current_user.id, data)
    return entry
