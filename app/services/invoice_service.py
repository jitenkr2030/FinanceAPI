from sqlalchemy.orm import Session
from app.models.invoice import Invoice

def create_invoice(db: Session, user_id: int, data):
    total = data.amount + (data.amount * data.tax / 100)

    invoice = Invoice(
        user_id=user_id,
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        amount=data.amount,
        tax=data.tax,
        total=total
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return invoice
