from sqlalchemy.orm import Session
from app.models.tax import TaxRecord
from datetime import datetime

def calculate_tax(db: Session, user_id: int, data):
    tax_amount = data.income * data.tax_rate / 100

    record = TaxRecord(
        user_id=user_id,
        income=data.income,
        tax_rate=data.tax_rate,
        tax_amount=tax_amount,
        created_at=datetime.utcnow()
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record
