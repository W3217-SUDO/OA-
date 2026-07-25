from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "思法汇成法律服务机构管理系统"
    api_prefix: str = "/api/v1"
    app_env: str = "development"
    # 本机无 Docker 时默认使用 SQLite；Docker Compose 会通过环境变量覆盖为 PostgreSQL。
    database_url: str = "sqlite+aiosqlite:///./legal_platform.db"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "replace-this-before-production"
    initial_admin_username: str = "admin"
    initial_admin_password: str = ""
    initial_admin_display_name: str = "管理者"
    initial_admin_department: str = "上海分所"
    seed_demo_data: bool = True
    access_token_minutes: int = 720
    # Local non-Docker development falls back to uploads/; Docker/production
    # explicitly set minio:9000, preventing unavailable MinIO from blocking uploads.
    minio_endpoint: str = ""
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    dify_base_url: str = ""
    dify_api_key: str = ""
    sms_webhook_url: str = ""
    sms_webhook_token: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
