from sqlalchemy.orm import Session
from app.models.audit import AuditLog

def log_action(db: Session, user_id: int, action: str, entity: str, details: str = None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        details=details
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log
