from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TaxCalculate(BaseModel):
    income: float
    tax_rate: float

class TaxResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    income: float
    tax_rate: float
    tax_amount: float
    created_at: datetime
