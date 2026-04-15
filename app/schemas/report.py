from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_type: str
    file_path: Optional[str] = None
    created_at: datetime
