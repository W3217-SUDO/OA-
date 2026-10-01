"""外部 HTTP 回归的隔离服务与数据库闸门。"""

import json
import os
import unittest
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

from tests.environment import isolated_sqlite_file, isolated_storage_path, validate_test_environment


def require_test_service() -> str:
    if not os.environ.get("OA_TEST_API_BASE"):
        raise unittest.SkipTest("必须显式设置 OA_TEST_API_BASE")
    environment = validate_test_environment()
    base = os.environ["OA_TEST_API_BASE"].rstrip("/")
    url = urlsplit(base)
    if (
        url.scheme != "http"
        or url.hostname not in {"localhost", "127.0.0.1", "::1"}
        or url.port is None
        or url.path != "/api/v1"
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise RuntimeError("OA_TEST_API_BASE 必须是显式本机 HTTP /api/v1 服务地址")
    with urllib.request.urlopen(f"{base}/testing/health", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"测试入口健康检查失败：HTTP {response.status}")
        payload = json.load(response)
    if payload != {"service": "oa-local-testing", "app_env": environment["APP_ENV"].strip().lower()}:
        raise RuntimeError("目标服务不是当前隔离测试入口")
    return base


def isolated_database_path() -> Path:
    database = make_url(os.environ["DATABASE_URL"])
    if database.drivername != "sqlite+aiosqlite" or database.database == ":memory:":
        raise RuntimeError("外部 HTTP 用例的直接数据库检查要求隔离 SQLite 文件")
    return isolated_sqlite_file(database.database or "", "DATABASE_URL")


def isolated_upload_root() -> Path:
    return isolated_storage_path(os.environ.get("UPLOAD_ROOT", ""), "UPLOAD_ROOT", directory=True)


def required_legacy_directory(variable: str) -> Path:
    raw = os.environ.get(variable)
    if not raw:
        raise unittest.SkipTest(f"必须显式设置 {variable}")
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise RuntimeError(f"{variable} 目录不存在：{path}")
    return path
