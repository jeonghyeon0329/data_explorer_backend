from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class _Settings(BaseSettings):
    host: str
    port: int
    app_env: str
    debug: bool
    db_url: Optional[str] = None
    minio_endpoint: Optional[str] = None
    minio_access_key: Optional[str] = None
    minio_secret_key: Optional[str] = None
    minio_secure: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def reload(self) -> bool:
        return self.debug or self.app_env != "prod"

settings = _Settings()
