from sqlalchemy.orm import Session
from app.models.audit import AuditLog

def get_audit_logs(db: Session, user_id: int):
    return db.query(AuditLog).filter(AuditLog.user_id == user_id).all()
