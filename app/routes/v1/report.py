from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.services.report_service import create_report
from app.services.analytics_service import get_financial_summary

from app.schemas.report import ReportResponse

router = APIRouter(prefix="/report", tags=["Report"])


@router.post("/create", response_model=ReportResponse)
def create_report_api(
    report_type: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    report = create_report(db, current_user.id, report_type)
    return report


@router.get("/summary")
def get_summary_api(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    summary = get_financial_summary(db, current_user.id)
    return summary
