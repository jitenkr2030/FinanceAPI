from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from datetime import datetime
from app.db.base import Base

class RecurringInvoice(Base):
    __tablename__ = "recurring_invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)

    amount = Column(Float, nullable=False)
    tax = Column(Float, nullable=False)
    currency = Column(String, default="USD")

    frequency = Column(String, nullable=False)  # weekly, monthly, quarterly
    next_due_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
