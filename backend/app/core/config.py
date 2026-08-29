from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str = "Image Quality AI"
    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite+aiosqlite:///./image_quality.db"
    UPLOAD_DIR: Path = Path("uploads")
    MODEL_DIR: Path = Path("models")
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    MODEL_VERSION: str = "1.0"
    
    class Config:
        env_file = ".env"

settings = Settings()
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.MODEL_DIR.mkdir(exist_ok=True)