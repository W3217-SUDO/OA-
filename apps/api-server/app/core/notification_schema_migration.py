"""通知发件箱和生成调度的独立增量结构。"""

from sqlalchemy.engine import Connection

from app.models import NotificationDelivery, NotificationSyncSchedule


def upgrade_notification_delivery_schema(connection: Connection) -> None:
    """由启动迁移修订注册；重复执行不会覆盖既有发送状态。"""
    NotificationDelivery.__table__.create(connection, checkfirst=True)
    NotificationSyncSchedule.__table__.create(connection, checkfirst=True)
