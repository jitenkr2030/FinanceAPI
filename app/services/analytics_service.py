from sqlalchemy.orm import Session
from app.models.invoice import Invoice

def get_financial_summary(db: Session, user_id: int):
    invoices = db.query(Invoice).filter(Invoice.user_id == user_id).all()

    total_revenue = sum(i.total for i in invoices)
    total_invoices = len(invoices)

    return {
        "total_revenue": total_revenue,
        "total_invoices": total_invoices
    }
