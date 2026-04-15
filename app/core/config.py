import os

class Settings:
    PROJECT_NAME = "Finance API SaaS"
    VERSION = "1.0.0"

    API_V1_STR = "/api/v1"

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///./finance.db"
    )

    SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret")

    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

settings = Settings()
