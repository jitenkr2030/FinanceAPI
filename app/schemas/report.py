from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ReportResponse(BaseModel):
    id: int
    report_type: str
    file_path: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
