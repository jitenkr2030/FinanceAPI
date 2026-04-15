from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Create user
class UserCreate(BaseModel):
    name: str
    email: EmailStr

# Response model
class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    api_key: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
