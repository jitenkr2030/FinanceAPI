from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.schemas.tax import TaxCalculate, TaxResponse
from app.services.tax_service import calculate_tax

router = APIRouter(prefix="/tax", tags=["Tax"])


@router.post("/calculate", response_model=TaxResponse)
def calculate_tax_api(
    data: TaxCalculate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    record = calculate_tax(db, current_user.id, data)
    return record
