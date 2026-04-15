from pydantic import BaseModel
from typing import Optional

class ResponseBase(BaseModel):
    success: bool = True
    message: Optional[str] = None

class Pagination(BaseModel):
    total: int
    page: int
    size: int
