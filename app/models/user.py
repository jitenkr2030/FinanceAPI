from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    api_key = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
