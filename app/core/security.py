import secrets
import bcrypt

def generate_api_key():
    return secrets.token_hex(16)

def verify_api_key(provided_key: str, stored_key: str):
    return secrets.compare_digest(provided_key, stored_key)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
