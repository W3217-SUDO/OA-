"""验证本地测试入口只能使用隔离数据库和附件目录。"""

import os
import re
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

if TYPE_CHECKING:
    from app.config import Settings


TEST_APP_ENVS = frozenset({"development", "dev", "test", "testing"})
_TEST_RUNTIME_ROOT = (Path(__file__).resolve().parent / ".runtime").resolve()
_TEMP_ROOT = Path(gettempdir()).resolve()
_TEST_DATABASE_NAME = re.compile(r"oa_test_[A-Za-z0-9_]+\Z")
_LOCAL_POSTGRES_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})

if _TEST_RUNTIME_ROOT != Path(__file__).resolve().parent / ".runtime":
    raise RuntimeError("tests/.runtime 不能指向测试目录以外")


def isolated_storage_path(raw_path: str, name: str, *, directory: bool) -> Path:
    if not raw_path or not raw_path.strip():
        raise RuntimeError(f"本地测试要求显式设置 {name}")
    path = Path(raw_path).expanduser().resolve()
    if path == _TEST_RUNTIME_ROOT:
        if directory:
            return path
        raise RuntimeError(f"{name} 必须指向 tests/.runtime 内的数据库文件")
    if path.is_relative_to(_TEST_RUNTIME_ROOT):
        return path
    if path.is_relative_to(_TEMP_ROOT):
        relative_parts = path.relative_to(_TEMP_ROOT).parts
        if (
            relative_parts
            and relative_parts[0].lower().startswith("oa-test-")
            and len(relative_parts[0]) > len("oa-test-")
            and (directory or len(relative_parts) > 1)
        ):
            return path
    raise RuntimeError(f"{name} 必须位于 tests/.runtime 或系统临时目录的 oa-test-* 专属子目录")


def isolated_sqlite_file(raw_path: str, name: str) -> Path:
    path = isolated_storage_path(raw_path, name, directory=False)
    if path.name.lower() == "legal_platform.db":
        raise RuntimeError(f"{name} 不能使用默认 legal_platform.db")
    if path.is_dir():
        raise RuntimeError(f"{name} 必须指向数据库文件")
    return path


def validate_database_url(raw_url: str) -> None:
    if not raw_url or not raw_url.strip():
        raise RuntimeError("本地测试要求显式设置 DATABASE_URL")
    try:
        url = make_url(raw_url)
    except ArgumentError as exc:
        raise RuntimeError("本地测试 DATABASE_URL 格式无效") from exc
    if url.query:
        raise RuntimeError("本地测试 DATABASE_URL 不允许附加查询参数")
    if url.drivername == "sqlite+aiosqlite":
        if url.host or not url.database:
            raise RuntimeError("本地测试 SQLite URL 必须使用明确的内存库或隔离文件")
        if url.database == ":memory:":
            return
        isolated_sqlite_file(url.database, "DATABASE_URL")
        return
    if url.drivername in {"postgresql+asyncpg", "postgresql+psycopg"}:
        if url.host not in _LOCAL_POSTGRES_HOSTS or not _TEST_DATABASE_NAME.fullmatch(url.database or ""):
            raise RuntimeError("本地测试 PostgreSQL 只允许本机或 postgres 主机上的 oa_test_* 数据库")
        return
    raise RuntimeError("本地测试只允许 SQLite aiosqlite 或 PostgreSQL 异步驱动")


def validate_test_environment() -> dict[str, str]:
    values = {key: os.environ.get(key, "") for key in ("APP_ENV", "DATABASE_URL", "UPLOAD_ROOT")}
    if values["APP_ENV"].strip().lower() not in TEST_APP_ENVS:
        raise RuntimeError("本地测试入口要求显式设置 APP_ENV=development/dev/test/testing")
    validate_database_url(values["DATABASE_URL"])
    upload_root = isolated_storage_path(values["UPLOAD_ROOT"], "UPLOAD_ROOT", directory=True)
    if upload_root.is_file():
        raise RuntimeError("本地测试 UPLOAD_ROOT 必须指向目录")
    return values


def validate_loaded_test_settings(settings: "Settings") -> None:
    """已加载的应用配置必须与通过隔离校验的环境一致。"""
    environment = validate_test_environment()
    if settings.app_env.strip().lower() != environment["APP_ENV"].strip().lower():
        raise RuntimeError("本地测试入口 APP_ENV 与已加载应用配置不一致")
    if settings.database_url != environment["DATABASE_URL"]:
        raise RuntimeError("本地测试入口 DATABASE_URL 与已加载应用配置不一致")
    if settings.upload_root != environment["UPLOAD_ROOT"]:
        raise RuntimeError("本地测试入口 UPLOAD_ROOT 与已加载应用配置不一致")
