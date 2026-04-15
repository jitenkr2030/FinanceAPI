from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import generate_api_key

def register_user_service(db: Session, name: str, email: str):
    api_key = generate_api_key()

    user = User(
        name=name,
        email=email,
        api_key=api_key
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
