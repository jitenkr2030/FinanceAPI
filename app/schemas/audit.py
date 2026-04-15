from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AuditResponse(BaseModel):
    id: int
    action: str
    entity: str
    details: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
