from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.security import generate_api_key
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
def register_user(data: UserCreate, db: Session = Depends(get_db)):

    api_key = generate_api_key()

    user = User(
        name=data.name,
        email=data.email,
        api_key=api_key
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
