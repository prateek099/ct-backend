"""Application settings loaded from env (pydantic-settings)."""
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict

# Prateek: Resolve .env relative to this file so the path is correct regardless of
# the working directory the server is started from (local, Docker, CI, etc.).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
_env_loaded = load_dotenv(_ENV_FILE, override=False)


class Settings(BaseSettings):
    # App
    app_name: str = "Creator Tools API"
    debug: bool = False
    environment: str = "development"  # development | staging | production

    # Prateek: Default targets the docker-compose Postgres service so `docker compose up`
    # works without tweaking .env. Render injects DATABASE_URL in production. The engine
    # normalises postgres:// → postgresql+psycopg:// at startup, so pasting Render's URL
    # verbatim is fine.
    database_url: str = "postgresql+psycopg://ct_user:ct_pass@db:5432/creator_tools"

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
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    # SMTP — transactional emails (welcome email, password reset, etc.)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Creator Tools"
    smtp_use_tls: bool = True

    # Frontend
    frontend_url: str = "http://localhost:5173"
    # frontend_url: str = "https://ct-frontend-awdz.onrender.com/"

    # Prateek: Demo credentials for the /login endpoint — base64-decoded at the wire.
    # Override via DEMO_USERNAME / DEMO_PASSWORD env vars in production.
    demo_username: str = "u"
    demo_password: str = "p"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" | "pretty"

    # Prateek: No env_file here — dotenv already loaded the .env into os.environ above.
    # pydantic-settings reads from os.environ; system env vars (Render, Docker) take
    # priority over .env values because load_dotenv uses override=False.
    model_config = SettingsConfigDict(extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()

_OPTIONAL_VARS: list[tuple[str, str]] = [
    ("openai_api_key", "OPENAI_API_KEY — AI generation endpoints will fail"),
    ("youtube_api_key", "YOUTUBE_API_KEY — YouTube channel endpoints will fail"),
]

_INSECURE_JWT = "change-me-in-production-use-openssl-rand-hex-32"


def _mask_db_url(url: str) -> str:
    # Prateek: Hide the password in DATABASE_URL so it's safe to log.
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        if parsed.password:
            masked = parsed._replace(netloc=parsed.netloc.replace(parsed.password, "****"))
            return urlunparse(masked)
    except Exception:
        pass
    return url


def check_optional_settings() -> None:
    # Prateek: Log .env load status first so operators know the source of config values.
    if _env_loaded:
        logger.info("Environment loaded from {}", _ENV_FILE)
    else:
        logger.warning(".env file not found at {} — relying on system environment variables", _ENV_FILE)

    logger.info(
        "Config | app={} env={} debug={} log_level={} log_format={} "
        "db={} cors={} jwt_algo={} access_ttl={}min refresh_ttl={}d "
        "openai={} youtube={}",
        settings.app_name,
        settings.environment,
        settings.debug,
        settings.log_level,
        settings.log_format,
        _mask_db_url(settings.database_url),
        settings.cors_origins,
        settings.jwt_algorithm,
        settings.jwt_access_token_expire_minutes,
        settings.jwt_refresh_token_expire_days,
        "set" if settings.openai_api_key else "MISSING",
        "set" if settings.youtube_api_key else "missing",
    )

    for attr, label in _OPTIONAL_VARS:
        if not getattr(settings, attr):
            logger.warning("Missing env var: {}", label)

    if settings.jwt_secret_key == _INSECURE_JWT:
        logger.warning("JWT_SECRET_KEY is using the insecure default — set a real secret in production")
