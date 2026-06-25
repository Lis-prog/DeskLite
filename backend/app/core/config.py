from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    # Database
    database_url: str = (
        "postgresql+psycopg://desklite:devpassword_change_me@db:5432/desklite"
    )

    # Auth / JWT
    jwt_secret: str = "change_me_to_a_long_random_string"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    # Set the `Secure` flag on auth cookies. Keep False for local http dev;
    # set True in any environment served over https.
    cookie_secure: bool = False
    # Share auth cookies between app + api subdomains (e.g. 158-220-114-100.sslip.io).
    # Leave empty for localhost / single-origin deploys where API and UI share one host.
    cookie_domain: str = ""

    # Object storage (MinIO / S3)
    s3_endpoint: str = "http://minio:9000"
    # Browser-facing MinIO URL for presigned downloads (e.g. https://files.example.com).
    # Leave empty in dev to use s3_endpoint; must be set in production behind a reverse proxy.
    s3_public_endpoint: str = ""
    s3_bucket: str = "desklite-attachments"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin_change_me"

    # CORS
    frontend_origin: str = "http://localhost:3000"

    # SLA: hours from creation until an unresolved ticket is flagged "overdue".
    # Configurable per priority via env (SLA_HOURS_URGENT, etc.).
    sla_hours_urgent: int = 4
    sla_hours_high: int = 24
    sla_hours_medium: int = 72
    sla_hours_low: int = 168

    # production disables Swagger UI on the public API
    app_env: str = "development"

    # Auth brute-force throttling (per client IP, sliding window)
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_max: int = 10
    auth_rate_limit_window_seconds: int = 60

    # Observability
    log_level: str = "INFO"
    # Emit single-line JSON logs (good for aggregation). When unset, defaults to
    # JSON in production and human-readable console logs elsewhere.
    log_json: bool | None = None
    # Sentry DSN for unhandled error reporting. Leave empty to disable (local dev/CI).
    sentry_dsn: str = ""


    @property
    def s3_presign_endpoint(self) -> str:
        """Endpoint embedded in presigned URLs (must match what the browser can reach)."""
        return self.s3_public_endpoint.strip() or self.s3_endpoint

    @property
    def use_json_logs(self) -> bool:
        """Resolve the effective log format, defaulting to JSON in production."""
        if self.log_json is not None:
            return self.log_json
        return self.app_env.lower() == "production"


settings = Settings()
