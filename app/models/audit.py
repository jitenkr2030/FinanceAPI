from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    action = Column(String, nullable=False)  # e.g., "create_invoice", "update_tax"
    entity = Column(String, nullable=False)  # e.g., "invoice", "tax"
    details = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
