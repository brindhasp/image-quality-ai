import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings:
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BACKEND_DIR, 'data', 'image_quality.db')}",
    )
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    MODEL_VERSION: str = os.getenv("MODEL_VERSION", "1.0")
    MODEL_PATH: str = os.getenv(
        "MODEL_PATH",
        os.path.join(BACKEND_DIR, "models", "image_quality_model.joblib"),
    )
    UPLOAD_DIR: str = os.getenv(
        "UPLOAD_DIR",
        os.path.join(BACKEND_DIR, "data", "uploads"),
    )
    ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "webp"}

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
