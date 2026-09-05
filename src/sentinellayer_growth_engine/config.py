from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration."""

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    database_url: str
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
