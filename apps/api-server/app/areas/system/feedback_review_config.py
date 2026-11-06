"""问题处理中心的审核设置：审核人和免审账号（用户要求，2026-11-06：默认这些人，页面上可以换）。

存在 system_configs（key=feedback_review），改动由数据变更留痕记下谁、什么时候、从谁改成谁。
没配置过或内容不对时用默认值，审核门不会因为配置问题被关掉。审核人只有一个。
"""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemConfig, User

CONFIG_KEY = "feedback_review"
DEFAULT_REVIEWER = "fwl"
DEFAULT_EXEMPT = ("fwl", "tgn", "shenhe")
# 自动化身份：不能改设置，不能当审核人，也不能进免审名单，否则会话能绕过审核。
BOT_USERNAME = "feedback-bot"


@dataclass(frozen=True)
class ReviewConfig:
    reviewer: str
    exempt: frozenset[str]


def _defaults() -> ReviewConfig:
    return ReviewConfig(DEFAULT_REVIEWER, frozenset(DEFAULT_EXEMPT))


def parse_review_config(value) -> ReviewConfig:
    if not isinstance(value, dict):
        return _defaults()
    reviewer = value.get("reviewer")
    exempt = value.get("exempt")
    if not isinstance(reviewer, str) or not reviewer.strip() or reviewer.strip() == BOT_USERNAME:
        return _defaults()
    if not isinstance(exempt, list) or not all(isinstance(item, str) for item in exempt):
        return _defaults()
    return ReviewConfig(reviewer.strip(), frozenset(item for item in exempt if item != BOT_USERNAME))


async def load_review_config(db: AsyncSession) -> ReviewConfig:
    return parse_review_config(await db.scalar(select(SystemConfig.value).where(SystemConfig.key == CONFIG_KEY)))


async def active_reviewer(db: AsyncSession, config: ReviewConfig) -> User | None:
    """当前审核人的在职账号；停用或不存在时返回 None，单子留在待审核，等管理员换人。"""
    return await db.scalar(select(User).where(User.username == config.reviewer, User.is_active.is_(True)))
