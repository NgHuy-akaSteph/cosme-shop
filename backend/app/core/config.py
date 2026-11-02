from pathlib import Path

from pydantic_settings import BaseSettings

# Lấy đường dẫn thư mục chứa config.py (backend/)
CONFIG_DIR = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    PORT: int = 8000

    # Tự chạy `alembic upgrade head` khi start app (mặc định tắt cho production)
    AUTO_MIGRATE: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://admin:secret@localhost:5432/cosme_shop"
    
    # Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 86400  # 1 day
    
    # CORS
    CORS_ORIGINS: str = '["http://localhost:5173"]'

    # SePay
    SEPAY_API_KEY: str = ""          # API Key xac thuc webhook (cach 1)
    SEPAY_WEBHOOK_SECRET: str = ""   # Secret Key HMAC-SHA256 (cach 2, khuyen nghi)
    SEPAY_BANK_ACCOUNT: str = ""
    SEPAY_BANK_NAME: str = ""
    SEPAY_API_TOKEN: str = ""        # Bearer token cho SePay API v2 (doi soat)
    SEPAY_API_BASE_URL: str = "https://userapi.sepay.vn/v2"

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    CLOUDINARY_UPLOAD_PRESET: str = "cosme_shop_unsigned"
    CLOUDINARY_FOLDER: str = "cosme-shop/products"
    CLOUDINARY_MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    
    class Config:
        env_file = CONFIG_DIR / ".env"  # Dùng Path thay vì string ".env"
        extra = "allow"  # Allow extra fields from env


settings = Settings()
