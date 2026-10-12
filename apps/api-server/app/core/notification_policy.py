"""案件费用自动提醒的统一抑制规则，保留审批和人工消息。"""

from sqlalchemy import String, and_, func, or_, select

from app.models import BusinessRecord, Notification


def case_fee_condition():
    data = BusinessRecord.data
    return and_(
        BusinessRecord.module == "finance",
        or_(
            func.coalesce(data["case_id"].as_string().cast(String), "").notin_(("", "0")),
            func.coalesce(data["case_record_id"].as_string().cast(String), "").notin_(("", "0")),
            func.trim(func.coalesce(data["case_no"].as_string(), "")) != "",
        ),
    )


def visible_notification_condition():
    linked_case_fee = select(BusinessRecord.id).where(
        BusinessRecord.id == Notification.source_id, case_fee_condition(),
    ).correlate(Notification).exists()
    return ~and_(
        Notification.source_type == "finance",
        func.coalesce(Notification.source_key, "").startswith("finance-approval-"),
        linked_case_fee,
    )
