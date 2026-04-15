from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity: str
    details: Optional[str] = None
    created_at: datetime
