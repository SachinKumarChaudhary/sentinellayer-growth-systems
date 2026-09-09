from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration."""

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    database_url: str
    database_connect_timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    database_statement_timeout_seconds: int = Field(default=30000, ge=1000, le=120000)
    real_email_enabled: bool = Field(default=False)
    smtp_host: str | None = Field(default=None)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = Field(default=None)
    smtp_password: str | None = Field(default=None)
    smtp_timeout_seconds: float = Field(default=30.0, gt=0)
    imap_host: str | None = Field(default=None)
    imap_port: int = Field(default=993, ge=1, le=65535)
    imap_username: str | None = Field(default=None)
    imap_password: str | None = Field(default=None)
    imap_mailbox: str = Field(default="INBOX")
    imap_timeout_seconds: float = Field(default=30.0, gt=0)
    scheduler_tick_seconds: int = Field(default=30, ge=1)
    tinyfish_api_key: str | None = Field(default=None)
    tinyfish_search_url: str = Field(default="https://api.search.tinyfish.ai")
    tinyfish_fetch_url: str = Field(default="https://api.fetch.tinyfish.ai")
    tinyfish_timeout_seconds: float = Field(default=20.0, gt=0)
    tinyfish_search_per_minute: int = Field(default=27, ge=1, le=30)
    tinyfish_search_per_hour: int = Field(default=450, ge=1, le=500)
    tinyfish_fetch_urls_per_minute: int = Field(default=135, ge=1, le=150)
    tinyfish_fetch_urls_per_day: int = Field(default=900, ge=1, le=1000)
    tinyfish_max_retry_attempts: int = Field(default=2, ge=1, le=8)

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
        if self.real_email_enabled:
            missing = [
                name
                for name, value in {
                    "SL_SMTP_HOST": self.smtp_host,
                    "SL_SMTP_USERNAME": self.smtp_username,
                    "SL_SMTP_PASSWORD": self.smtp_password,
                }.items()
                if not value
            ]
            if missing:
                raise RuntimeError(f"Missing required SMTP settings: {', '.join(missing)}")
            if self.smtp_port not in (465, 587):
                raise RuntimeError("SL_SMTP_PORT must be 465 or 587")
