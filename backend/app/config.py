from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    """Application configuration settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields like OAuth config (handled by figma_oauth.py)
    )
    
    # Application
    APP_NAME: str = "Pixel Perfect UI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Frontend URL (for OAuth redirects)
    FRONTEND_URL: str = "http://localhost:5173"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    @field_validator('CORS_ORIGINS', mode='before')
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    STATIC_DIR: str = "static"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Figma API
    FIGMA_API_BASE_URL: str = "https://api.figma.com/v1"
    FIGMA_DEFAULT_SCALE: int = 2  # 2x for retina
    
    # Website Capture
    PLAYWRIGHT_TIMEOUT: int = 30000  # 30 seconds
    DEFAULT_VIEWPORT_WIDTH: int = 1920
    DEFAULT_VIEWPORT_HEIGHT: int = 1080
    
    # Comparison Settings
    COLOR_TOLERANCE: int = 5  # Delta E tolerance
    SPACING_TOLERANCE: int = 2  # Pixels
    PIXEL_DIFF_THRESHOLD: float = 0.95  # SSIM threshold
    
    # Database (PostgreSQL)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/pixel_perfect_ui"
    
    # Environment (development/production)
    ENVIRONMENT: str = "development"
    
    # AWS S3 Configuration (for production profile image storage)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "ap-southeast-1"
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_CUSTOM_DOMAIN: Optional[str] = None  # Optional: CloudFront or custom domain


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
