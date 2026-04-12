from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "Creator Tools API"
    debug: bool = False
    environment: str = "development"  # development | staging | production

    # Database
    database_url: str = "sqlite:///./ct.db"

    # JWT
    jwt_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "http://localhost:5173"

    # External APIs
    openai_api_key: str = ""
    youtube_api_key: str = ""

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" | "pretty"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
