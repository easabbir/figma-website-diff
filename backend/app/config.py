from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Application
    APP_NAME: str = "Figma-Website UI Comparison Tool"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
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
    
    # Redis (for Celery)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
