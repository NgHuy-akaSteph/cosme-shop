from pathlib import Path

from pydantic_settings import BaseSettings

# Lấy đường dẫn thư mục chứa config.py (backend/)
CONFIG_DIR = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://admin:secret@localhost:5432/cosme_shop"
    
    # Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 86400  # 1 day
    
    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000"]'

    # SePay
    SEPAY_API_KEY: str = ""
    SEPAY_BANK_ACCOUNT: str = ""
    SEPAY_BANK_NAME: str = ""

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
