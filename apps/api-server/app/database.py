import json

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings
from .core.request_metrics import install_query_metrics


class Base(DeclarativeBase):
    pass


def dumps_json(value) -> str:
    """JSON 列保留中文：data 按文本搜索时，\\uXXXX 形式的中文搜不到（案件保存后案号、当事人搜不到）。"""
    return json.dumps(value, ensure_ascii=False)


def _engine_options(url: str) -> dict:
    """PostgreSQL 连接一律每次按实际参数规划（plan_cache_mode=force_custom_plan）。

    预编译语句执行几次后 PostgreSQL 可能改用通用计划，不看具体模块，把 8 千多行估成几十行、选嵌套循环，
    一条费用查询从 0.25 秒变成 17 秒（生产最长 37.5 秒，11-06 慢查询评估）。每次规划约 0.1 毫秒，可以忽略。
    只影响本应用的连接；同步程序用自己的连接，不受影响。
    """
    if url.startswith("postgresql+asyncpg"):
        return {"connect_args": {"server_settings": {"plan_cache_mode": "force_custom_plan"}}}
    return {}


engine = create_async_engine(settings.database_url, pool_pre_ping=True, json_serializer=dumps_json,
                             **_engine_options(settings.database_url))
install_query_metrics(engine)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with SessionLocal() as session:
        yield session
