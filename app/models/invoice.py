from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from app.db.base import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)

    amount = Column(Float, nullable=False)
    tax = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

    status = Column(String, default="pending")  # pending, paid, cancelled

    created_at = Column(DateTime, default=datetime.utcnow)
