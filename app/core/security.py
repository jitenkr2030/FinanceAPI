import secrets

# Generate secure API key
def generate_api_key():
    return secrets.token_hex(16)

# Simple API key verification (will connect to DB later)
def verify_api_key(provided_key: str, stored_key: str):
    return secrets.compare_digest(provided_key, stored_key)
