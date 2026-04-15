from sqlalchemy.orm import Session
from app.models.user import User

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, name: str, email: str, api_key: str):
    user = User(name=name, email=email, api_key=api_key)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
