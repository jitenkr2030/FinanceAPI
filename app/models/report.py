from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.db.base import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    report_type = Column(String, nullable=False)  # e.g., "monthly", "tax", "audit"
    file_path = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
