from pydantic import BaseModel
from datetime import datetime

# Tax calculation input
class TaxCalculate(BaseModel):
    income: float
    tax_rate: float

# Tax response
class TaxResponse(BaseModel):
    income: float
    tax_rate: float
    tax_amount: float
    created_at: datetime

    class Config:
        orm_mode = True
