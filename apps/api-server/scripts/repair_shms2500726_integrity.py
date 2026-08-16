"""Idempotently repair the migrated SHMS2500726 aggregate from verified 8091 rows."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent


def legacy_time(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=ZoneInfo("Asia/Shanghai"))


async def run() -> None:
    async with SessionLocal() as db:
        records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.serial_no.in_({"SHMS2500726", "SHHT2510044", "SHKH2511089"})))).all())
        by_no = {item.serial_no: item for item in records}
        case = by_no["SHMS2500726"]
        contract = by_no["SHHT2510044"]
        customer = by_no["SHKH2511089"]

        for username, display_name in {"haoyun": "郝蕴", "wbhzls": "外部合作律师", "fanyg": "范应根"}.items():
            user = await db.scalar(select(User).where(User.username == username))
            if user:
                user.display_name = display_name

        customer.title = customer.customer = "三河市启科电子商务有限公司"
        customer.owner = "wbhzls"
        customer.created_at = legacy_time("2025-07-03T09:28:23.417")
        customer.updated_at = legacy_time("2025-07-03T09:43:47.060")
        customer.data = {**(customer.data or {}), "legacy_customer_id": 15388, "customer_no": customer.serial_no, "customer_id": customer.id, "customer_record_id": customer.id, "customer_title": customer.title, "legal_agent_name": "周立芬", "license_no": "91131082MADBMY0W5K", "registration_address": "河北省廊坊市三河市燕郊开发区行宫东大街南侧中弘大厦726A"}

        case.status = "文书准备"
        case_data = dict(case.data or {})
        case.data = {**case_data, "case_phase_id": 101011, "source_person": "wbhzls", "handling_lawyers": ["王晓英"], "handling_lawyer_usernames": ["wangxy"], "assistant": "郝蕴", "assistant_username": "haoyun", "investigator": "haoyun,haoyun", "investigator_display_name": "郝蕴,郝蕴", "case_register_date": "2025-10-23T15:39:08.523", "case_divisional_date": "2026-04-14T09:13:36", "plaintiff": "三河市启科电子商务有限公司", "defendant": "东莞市东城梦讯美百货商行（个体工商户）", "opponent": "东莞市东城梦讯美百货商行（个体工商户）", "notarial_no": "(2025)赣洪江证内字第4374号", "warehouse": "上海一仓(3-2)", "customer_id": customer.id, "customer_record_id": customer.id, "customer_no": customer.serial_no, "customer_title": customer.title, "contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract.serial_no, "contract_title": contract.title}

        metadata = {
            (contract.id, "20250704131853382_三河启科电子商务和申浩.pdf"): ("haoyun", "2025-07-04T13:18:53.383"),
            (customer.id, "三河启科电子商务和申浩.pdf"): ("haoyun", "2025-07-04T13:03:02.820"),
            (case.id, "友帮手品牌调查指南.pdf"): ("haoyun", "2025-07-09T09:40:25.217"),
            (case.id, "微信图片_20250828160744_101_112.png"): ("haoyun", "2025-10-23T15:05:37.783"),
            (case.id, "微信图片_20250828160800_105_112.png"): ("haoyun", "2025-10-23T15:05:48.247"),
        }
        attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id.in_({case.id, contract.id, customer.id})))).all())
        for attachment in attachments:
            if attachment.record_id == case.id and attachment.original_name == "友帮手品牌介绍演示文稿1.pdf" and attachment.uploader == "legacy-migration":
                await db.delete(attachment)
                continue
            values = metadata.get((attachment.record_id, attachment.original_name))
            if values:
                attachment.uploader, created_at = values
                attachment.created_at = legacy_time(created_at)
        evidence_rows = sorted([item for item in attachments if item.record_id == case.id and item.original_name == "(2025)赣洪江证内字第4374号.pdf"], key=lambda item: item.id)
        for attachment, uploader, created_at in zip(evidence_rows, ("fanyg", "fanyg"), ("2025-12-10T09:46:37.270", "2025-12-10T14:29:55.853")):
            attachment.uploader = uploader
            attachment.created_at = legacy_time(created_at)

        fee = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "finance", BusinessRecord.data["legacy_case_fee_id"].as_integer() == 40175))
        if fee is None:
            fee = BusinessRecord(module="finance", serial_no="JF40175", title="公证费", customer=customer.title, status="历史数据", owner="haoyun", department=case.department, description="公证号:(2025)赣洪江证内字第4374号;费用类型: 公证费", created_at=legacy_time("2025-10-23T15:41:08.297"), updated_at=legacy_time("2025-10-23T15:41:08"))
            db.add(fee)
            await db.flush()
            db.add(WorkflowEvent(record_id=fee.id, action="迁移旧系统律所费用", to_status=fee.status, operator="legacy-import", comment="旧系统案件费用ID 40175"))
        fee.data = {"migration_source": "legacy_prd_crm", "legacy_case_fee_id": 40175, "legacy_case_fee_guid": "4fa3ca34-30d4-4854-9a4f-532a54f80339", "case_id": case.id, "case_record_id": case.id, "case_no": case.serial_no, "case_title": case.title, "contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract.serial_no, "contract_title": contract.title, "customer_id": customer.id, "customer_record_id": customer.id, "customer_no": customer.serial_no, "customer_title": customer.title, "expense_scope": "律所", "expense_subtype": "公证费", "fee_type": "官方费用", "amount": 300.0, "payment_requested_amount": 300.0, "paid_amount": 300.0, "submitted_at": "2025-10-23T15:41:08.297", "submitted_by": "haoyun", "submitted_by_display_name": "郝蕴", "payment_deadline": "2025-10-30", "refund_amount": 0, "received_amount": 0}
        await db.commit()
        print({"case": case.serial_no, "status": case.status, "fee": fee.serial_no, "active_attachments": len(attachments) - 1})


if __name__ == "__main__":
    asyncio.run(run())
