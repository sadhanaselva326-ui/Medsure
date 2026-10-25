from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    APP_NAME: str = "MedSure Vision"
    DEBUG: bool = False
    SECRET_KEY: Optional[str] = None
    ADMIN_API_KEY: Optional[str] = None
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/medsure_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # API Keys
    ABDM_API_KEY: str = ""
    EKA_CARE_API_KEY: str = ""
    GS1_API_KEY: str = ""

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://medsure.vision"
    ]

    # Logging
    LOG_LEVEL: str = "INFO"

    # Search
    FUZZY_THRESHOLD: float = 0.3

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [item.strip() for item in v.split(",") if item.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]


settings = Settings()
