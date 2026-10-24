from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_LOCAL_DATABASE_PATH = (Path(__file__).resolve().parent.parent / "legal_platform.db").as_posix()


class Settings(BaseSettings):
    app_name: str = "思法汇成法律服务机构管理系统"
    api_prefix: str = "/api/v1"
    capability_catalog_path: str = ""
    app_env: str = "development"
    slow_request_log_seconds: float = Field(default=2, gt=0)
    # 本机无 Docker 时默认使用 SQLite；Docker Compose 会通过环境变量覆盖为 PostgreSQL。
    # Resolve the development SQLite database from this module, not the
    # process working directory. This keeps the local web/API pair on one
    # data source regardless of how uvicorn is launched.
    database_url: str = f"sqlite+aiosqlite:///{_LOCAL_DATABASE_PATH}"
    # Production releases share one attachment root so versioned worktrees do
    # not invalidate paths written by earlier releases.
    upload_root: str = ""
    attachment_delete_reconcile_min_age_seconds: int = Field(default=60, ge=0)
    redis_url: str = "redis://redis:6379/0"
    # 留空保留进程内缓存；共享缓存使用独立连接和逻辑数据库，不复用任务队列配置。
    cache_redis_url: str = ""
    cache_redis_max_connections: int = Field(default=16, ge=1, le=128)
    cache_redis_timeout_seconds: float = Field(default=1, gt=0, le=10)
    dashboard_metrics_cache_ttl_seconds: int = Field(default=86400, ge=1, le=86400)
    dashboard_metrics_cache_wait_seconds: float = Field(default=15, gt=0, le=60)
    dashboard_metrics_compute_timeout_seconds: float = Field(default=30, gt=0, le=120)
    # 每次命中都核对数据修订号，有效期只决定清理时机；键含业务日期，跨日自然失效。
    query_cache_ttl_seconds: int = Field(default=86400, ge=1, le=86400)
    # Redis 为 noeviction：已用内存超过上限的该比例后不再写入新结果，避免写满后加锁失败。
    query_cache_memory_ratio: float = Field(default=0.6, gt=0, le=0.9)
    # 后台预热：数据修订或业务日期变化后，由主进程替最近用过的查询重新算好结果。
    query_prewarm_enabled: bool = True
    query_prewarm_interval_seconds: float = Field(default=15, gt=0, le=600)
    query_prewarm_max_entries: int = Field(default=120, ge=1, le=2000)
    query_prewarm_idle_days: int = Field(default=4, ge=1, le=30)
    query_cache_max_payload_bytes: int = Field(default=4 * 1024 * 1024, ge=1024, le=64 * 1024 * 1024)
    # 费用筛选事实按列压缩存放（全所约 5 万笔费用压缩后数 MB），单独设上限。
    fee_facts_cache_max_payload_bytes: int = Field(default=24 * 1024 * 1024, ge=1024, le=128 * 1024 * 1024)
    secret_key: str = "replace-this-before-production"
    initial_admin_username: str = "admin"
    initial_admin_password: str = ""
    initial_admin_display_name: str = "管理者"
    initial_admin_department: str = "上海分所"
    seed_demo_data: bool = False
    access_token_minutes: int = 720
    # Office Online fetches documents server-to-server and therefore needs a
    # publicly trusted HTTPS origin rather than the user's authenticated OA URL.
    office_preview_public_base_url: str = ""
    office_editor_enabled: bool = False
    office_editor_validation_case_codes: list[str] = Field(default_factory=list)
    code_server_url: str = ""
    code_browser_url: str = ""
    office_wopi_base_url: str = ""
    office_frontend_origin: str = ""
    office_trusted_origins: list[str] = Field(default_factory=list)
    office_wopi_token_secret: str = ""
    office_editor_token_seconds: int = Field(default=3600, ge=300, le=14400)
    office_editor_lease_seconds: int = Field(default=1800, ge=60, le=1800)
    office_editor_max_file_bytes: int = Field(default=20 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    office_wopi_requests_per_minute: int = Field(default=120, ge=10, le=600)
    office_oss_write_prefix: str = ""
    # Local non-Docker development falls back to uploads/; Docker/production
    # explicitly set minio:9000, preventing unavailable MinIO from blocking uploads.
    minio_endpoint: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""
    oss_credentials_file: str = ""
    oss_endpoint: str = "oss-cn-shanghai.aliyuncs.com"
    oss_signed_url_expire_seconds: int = Field(default=600, ge=60, le=3600)
    ai_oss_bucket: str = ""
    ai_oss_prefix: str = ""
    ai_oss_endpoint: str = ""
    ai_oss_credentials_file: str = ""
    # 法院收文文件放在 AI 文件桶的独立目录（不在 AI空间 下）；桶未配置时退回本机附件目录。
    court_intake_oss_prefix: str = "法院收文"
    # 所有附件以 OSS 为准（AI 文件桶“附件/”目录），服务器上的文件只做缓存；新附件写入本机后由后台同步上 OSS 并切换路径。
    attachment_oss_prefix: str = "附件"
    attachment_oss_sync_delay_seconds: int = Field(default=120, ge=10, le=3600)
    dify_base_url: str = ""
    dify_api_key: str = ""
    langgraph_enabled: bool = False
    langgraph_checkpoint_url: str = ""
    langgraph_api_base_url: str = ""
    langgraph_api_key: str = ""
    langgraph_model_provider: str = ""
    langgraph_model: str = ""
    langgraph_max_concurrency: int = 4
    # 智能体运行时常驻：同一会话的后续提问复用已启动的运行时，空闲超时自动关停；0 表示关闭常驻（每轮冷启动）。
    agent_resident_idle_seconds: int = 600
    agent_resident_max_sessions: int = 2  # 每个 API 进程最多常驻几个会话；生产有多个进程，总数 = 进程数 × 此值
    agent_runtime_backend: Literal["deepseek-harness"] = "deepseek-harness"
    # 原生运行时负责上下文压缩；长期记忆程序按部署环境显式配置。
    deepseek_harness_root: str = ""
    deepseek_harness_cache_root: str = ""
    deepseek_harness_memory_command: str = ""
    deepseek_harness_skill_socket: str = ""
    deepseek_harness_plugin_path: str = ""
    # 个人智能体的身份文件和会话记录放在上传目录之外，不能被公开附件路由直接访问。
    personal_agent_root: str = ""
    sms_webhook_url: str = ""
    sms_webhook_token: str = ""
    dingtalk_corp_id: str = ""
    dingtalk_agent_id: str = ""
    dingtalk_app_key: str = ""
    dingtalk_app_secret: str = ""
    dingtalk_app_url: str = ""
    dingtalk_notifications_enabled: bool = True
    system_cache_ttl_seconds: int = 3600
    # Comma-separated OA display names allowed to bind and use DingTalk SSO.
    # Empty keeps the integration unrestricted for local development.
    dingtalk_allowed_display_names: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
