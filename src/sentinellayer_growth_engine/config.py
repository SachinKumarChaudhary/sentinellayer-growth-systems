from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration."""

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    database_url: str
    real_email_enabled: bool = Field(default=False)
    scheduler_tick_seconds: int = Field(default=30, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SL_",
        extra="ignore",
    )

    def assert_safe(self) -> None:
        """Prevent accidental real-email operation outside production."""
        if self.environment != "production" and self.real_email_enabled:
            raise RuntimeError(
                "SL_REAL_EMAIL_ENABLED must remain false outside production"
            )
