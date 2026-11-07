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


engine = create_async_engine(settings.database_url, pool_pre_ping=True, json_serializer=dumps_json)
install_query_metrics(engine)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with SessionLocal() as session:
        yield session
