from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Field(...) explicitly makes these required. If missing from .env, the app fails fast on startup.
    GEMINI_API_KEY: str = Field(...)
    MONGODB_URL: str = Field(...)

    DB_NAME: str = "ai_qa_db"
    UPLOAD_DIR: str = "uploads"
    FAISS_DIR: str = "faiss_indexes"
    MAX_FILE_SIZE_MB: int = 100

    # ── JWT Auth ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_REQUESTS: int = 30       # max requests per window
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # window duration

    class Config:
        env_file = ".env"

settings = Settings()
