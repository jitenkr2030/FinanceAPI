import secrets
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_api_key():
    return secrets.token_hex(16)

def verify_api_key(provided_key: str, stored_key: str):
    return secrets.compare_digest(provided_key, stored_key)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
