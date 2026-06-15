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

    # Object storage (MinIO / S3)
    s3_endpoint: str = "http://minio:9000"
    s3_bucket: str = "desklite-attachments"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin_change_me"

    # CORS
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
