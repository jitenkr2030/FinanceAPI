from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class LedgerCreate(BaseModel):
    entry_type: str
    amount: float
    description: Optional[str] = None

class LedgerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_type: str
    amount: float
    description: Optional[str] = None
    created_at: datetime
