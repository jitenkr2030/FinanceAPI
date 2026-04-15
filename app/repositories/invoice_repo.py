from sqlalchemy.orm import Session
from app.models.invoice import Invoice

def get_invoices_by_user(db: Session, user_id: int):
    return db.query(Invoice).filter(Invoice.user_id == user_id).all()
