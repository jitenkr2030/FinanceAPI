from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Create ledger entry
class LedgerCreate(BaseModel):
    entry_type: str  # credit / debit
    amount: float
    description: Optional[str]

# Response model
class LedgerResponse(BaseModel):
    id: int
    entry_type: str
    amount: float
    description: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
