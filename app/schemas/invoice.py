from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Create invoice
class InvoiceCreate(BaseModel):
    customer_name: str
    customer_email: Optional[EmailStr]
    amount: float
    tax: float

# Response model
class InvoiceResponse(BaseModel):
    id: int
    customer_name: str
    customer_email: Optional[EmailStr]
    amount: float
    tax: float
    total: float
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
