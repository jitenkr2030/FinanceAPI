from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    api_key = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)

    # Organisation & role
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    role = Column(String, default="admin")           # admin, accountant, viewer

    # Password reset
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Two-factor authentication (TOTP)
    totp_secret = Column(String, nullable=True)
    is_2fa_enabled = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
