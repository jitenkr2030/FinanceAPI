from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional

class InvoiceCreate(BaseModel):
    customer_name: str
    customer_email: Optional[EmailStr] = None
    amount: float
    tax: float

class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    customer_email: Optional[EmailStr] = None
    amount: float
    tax: float
    total: float
    status: str
    created_at: datetime
