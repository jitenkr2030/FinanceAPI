from sqlalchemy.orm import Session
from app.models.accounting import Ledger

def add_ledger_entry(db: Session, user_id: int, data):
    entry = Ledger(
        user_id=user_id,
        entry_type=data.entry_type,
        amount=data.amount,
        description=data.description
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return entry
