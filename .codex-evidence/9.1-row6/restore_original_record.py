"""Restore the read-only online row-6 snapshot into the isolated SQLite DB."""

from __future__ import annotations

import asyncio
from datetime import datetime
import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import BusinessRecord, FileAttachment, WorkflowEvent


async def main() -> None:
    engine = create_async_engine(os.environ["ROW6_DATABASE_URL"])
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        customer = BusinessRecord(
            id=644, module="customer", serial_no="SHKH2600002", title="测试客户8.3",
            customer="测试客户8.3", status="正常", owner="admin", department="上海分所", data={},
        )
        contract = BusinessRecord(
            id=47145, module="contract", serial_no="SHHT2673411", title="测试客户8.3合同11",
            customer="测试客户8.3", status="审批中", owner="admin", department="上海分所", description="饿",
            data={
                "amount": 0, "signed_at": "2026-09-01", "type": "法律顾问合同", "contract_body": "平台",
                "fee_type": "固定收费", "external_contract_numbers": [], "external_contract_no": "",
                "customer_id": 644, "customer_record_id": 644, "customer_no": "SHKH2600002",
                "customer_name": "测试客户8.3", "customer_manager": "admin、fwl、smoke_peer_manager_1785567320d4025",
                "contract_guid": "35b334fa-5842-4a62-8e70-83a5a8cf5fcd", "source_person": "fwl",
                "approval_count": 1, "submitted_at": "2026-09-01T13:22:00", "submitted_by": "admin",
                "submit_comment": "", "current_approver": "tgn", "sync_seal": True,
            },
            created_at=datetime.fromisoformat("2026-09-01T05:21:49.526062+00:00"),
            updated_at=datetime.fromisoformat("2026-09-01T05:22:13.502752+00:00"),
        )
        seal = BusinessRecord(
            id=47146, module="seal", serial_no="YY202609011322136E1", title="测试客户8.3合同11合同用印",
            customer="测试客户8.3", status="草稿", owner="admin", department="上海分所", data={
                "contract_record_id": 47145, "contract_no": "SHHT2673411", "use_type": "合同用印",
                "seal_asset_id": 7, "seal_type": "财务三排章", "seal_name": "申浩律师事务所财务三排章",
                "copies": 1, "purpose": "测试客户8.3合同11合同用印", "use_date": "2026-09-02",
                "delivery_method": "现场用印", "document_names": "SHMS2600436-结算提成表-20260901130504.docx",
                "approver": "admin", "source_attachment_ids": [665],
            },
            created_at=datetime.fromisoformat("2026-09-01T05:22:13.502752+00:00"),
            updated_at=datetime.fromisoformat("2026-09-01T05:22:13.502752+00:00"),
        )
        contract.data = {**contract.data, "seal_application_id": seal.id, "seal_application_no": seal.serial_no,
                         "seal_requested_at": "2026-09-01T13:22:13"}
        db.add_all([customer, contract, seal])
        db.add(FileAttachment(
            id=665, record_id=seal.id, category="用印文件",
            original_name="SHMS2600436-结算提成表-20260901130504.docx", stored_name="row6-original-665.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=1,
            path=os.environ["ROW6_ATTACHMENT_PATH"], uploader="admin",
        ))
        db.add_all([
            WorkflowEvent(record_id=contract.id, action="提交合同审批", from_status="草稿", to_status="审批中", operator="admin"),
            WorkflowEvent(record_id=seal.id, action="生成用印申请", from_status="", to_status="草稿", operator="admin",
                          comment="来源合同 SHHT2673411；线上只读快照仍为草稿"),
        ])
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
