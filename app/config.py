from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Recorda API"
    environment: str = "development"
    debug: bool = True
    version: str = "0.1.0"


settings = Settings()
