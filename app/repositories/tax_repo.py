from sqlalchemy.orm import Session
from app.models.tax import TaxRecord

def get_tax_records(db: Session, user_id: int):
    return db.query(TaxRecord).filter(TaxRecord.user_id == user_id).all()
