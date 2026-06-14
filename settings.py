from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class _Settings(BaseSettings):
    host: str
    port: int
    app_env: str
    debug: bool

    db_driver: str = "postgresql+psycopg"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "data_explorer"
    db_user: str = "postgres"
    db_password: str = ""

    minio_endpoint: Optional[str] = None
    minio_access_key: Optional[str] = None
    minio_secret_key: Optional[str] = None
    minio_secure: bool = True

    jwt_secret_key: str = "change-this-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def db_url(self) -> str:
        return f"{self.db_driver}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def reload(self) -> bool:
        return self.debug or self.app_env != "prod"

settings = _Settings()
