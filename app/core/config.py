from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Creator Tools API"
    debug: bool = False
    database_url: str = "sqlite:///./ct.db"

    class Config:
        env_file = ".env"


settings = Settings()
