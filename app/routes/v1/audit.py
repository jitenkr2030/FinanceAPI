from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.services.audit_service import log_action
from app.schemas.audit import AuditResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.post("/log", response_model=AuditResponse)
def log_audit_api(
    action: str,
    entity: str,
    details: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    log = log_action(db, current_user.id, action, entity, details)
    return log
