"""Restore the read-only online row-4 snapshot into an isolated SQLite DB."""

from __future__ import annotations

import asyncio
from datetime import datetime
import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent
from app.security import hash_password


DT = datetime.fromisoformat


async def main() -> None:
    database_url = os.environ["ROW4_DATABASE_URL"]
    upload_path = os.environ["ROW4_ATTACHMENT_PATH"]
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        password = hash_password(os.environ["ROW4_ADMIN_PASSWORD"])
        db.add_all([
            User(id=1, username="admin", display_name="陶威", department="上海分所", password_hash=password, role="admin", role_ids=["admin"], is_active=True),
            User(id=2, username="fwl", display_name="范文林", department="财务部", password_hash=password, role="manager", role_ids=["manager"], profile={"position": "财务人员"}, is_active=True),
            User(id=281, username="fanyg", display_name="范应根", department="调查取证部", password_hash=password, role="user", role_ids=["user"], profile={"position": "调查部部长"}, is_active=True),
            User(id=6, username="tgn", display_name="陶国南", department="知识产权中心", password_hash=password, role="admin", role_ids=["admin"], is_active=True),
        ])
        clue_data = {
            "product": "11", "source": "", "source_task_id": 3993, "source_task_no": "RW24154948210",
            "publisher": "fwl", "source_owner": "fanyg", "right_type": "商标", "sales_channel": "天猫",
            "platform": "天猫", "investigation_record_id": 28383, "investigation_no": "RW2415161928017",
            "submitted_at": "2026-08-17T10:28:14", "submitted_by": "fwl", "review_comment": "11",
            "reviewer": "admin", "reviewed_at": "2026-08-18T13:42:51", "material_categories": ["取证文件"],
            "material_count": 1, "collected_at": "2026-09-01", "notary_institution": "上海市东方公证处",
            "notarization_no": "1111", "certificate_no": "1111", "storage_location": "重庆一仓 / 重庆",
            "warehouse_id": 15, "warehouse_no": "CQ00001", "warehouse": "重庆一仓", "storage_location_id": 677,
            "storage_location_no": "CQ00001001", "location": "重庆", "evidence_status": "未入库",
            "collection_file_ids": [668], "collected_by": "admin", "collection_registered_at": "2026-09-01T15:50:39",
            "collection_evidence_record_id": 47149, "converted_case_id": 47150, "converted_case_no": "SHMS2600438",
        }
        case_data = {
            "contract_id": None, "contract_no": "", "clue_id": 4111, "clue_record_id": 4111,
            "investigation_clue_id": 4111, "investigation_clue_ids": [4111], "clue_no": "M26085930",
            "investigation_clue": "M26085930", "investigation_clue_nos": ["M26085930"], "case_type": "民事案件",
            "court": "上海市宝山区人民法院", "client_position": "原告", "cause_or_charge": "侵害商标权纠纷",
            "cause_of_action": "侵害商标权纠纷", "investigator": "fwl", "product": "11", "batch_converted": True,
            "case_creation_step": "completed", "case_creation_approval_status": "自动通过",
            "case_creation_approved_by": "system", "handling_lawyers": ["范文林"], "assistant": "范文林",
            "handling_lawyer_usernames": ["fwl"], "assistant_username": "fwl", "case_team_usernames": ["fwl"],
            "fixed_tasks_generated": True, "fixed_task_ids": [47151, 47152], "hearing_lawyer": "陶国南",
            "hearing_lawyer_username": "tgn", "first_instance_court": "上海市宝山区人民法院",
            "first_instance_case_no": "111", "courtroom": "知识产权法庭", "first_court_name": "上海市宝山区人民法院",
            "first_court_case_no": "111", "first_court_courtroom": "知识产权法庭",
            "first_court_hearing_date": "2026-09-02 00:00:00",
        }
        db.add_all([
            BusinessRecord(id=3993, module="task", serial_no="RW24154948210", title="测试555商标侵权调查", customer="测试555", status="历史数据", owner="fwl", department="上海分所", description="无", data={"investigation_record_id": 28383, "investigation_no": "RW2415161928017", "source_owner": "fanyg", "publisher": "fanyg"}, created_at=DT("2024-09-20T07:49:48.223000+00:00"), updated_at=DT("2024-09-20T07:49:48.223000+00:00")),
            # Online id 28383 currently resolves to this warehouse record, not an investigation record. Preserve that defect exactly.
            BusinessRecord(id=28383, module="warehouse", serial_no="WMS-LEGACY-2690", title="EV232215400245352", customer="", status="在库", owner="wangchanghong", department="历史仓库", data={"location": "10-3", "warehouse": "上海一仓", "legacy_evidence_id": 2690}, created_at=DT("2023-08-14T14:15:40.023000+00:00"), updated_at=DT("2026-08-25T18:32:03.690424+00:00")),
            BusinessRecord(id=4111, module="clue", serial_no="M26085930", title="11", customer="测试555", status="已转案件", owner="fwl", department="调查取证部", data=clue_data, created_at=DT("2026-08-17T02:28:14.936658+00:00"), updated_at=DT("2026-09-01T07:51:06.288426+00:00")),
            BusinessRecord(id=47149, module="evidence", serial_no="ZJ-M26085930", title="11—取证材料", customer="测试555", status="已取证", owner="fwl", department="调查取证部", data={"source": "线索取证登记", "clue_id": 4111, "clue_record_id": 4111, "clue_no": "M26085930", "evidence_type": "调查取证", "collected_at": "2026-09-01", "notary_institution": "上海市东方公证处", "notarization_no": "1111", "storage_location": "重庆一仓 / 重庆", "storage_state": "未入库", "evidence_file_ids": [668]}, created_at=DT("2026-09-01T07:50:39.357305+00:00"), updated_at=DT("2026-09-01T07:50:39.357305+00:00")),
            BusinessRecord(id=47150, module="case", serial_no="SHMS2600438", title="测试555侵害商标权纠纷11", customer="测试555", status="等待公证书", owner="fwl", department="调查取证部", description="由已取证线索 M26085930 自动转案", data=case_data, created_at=DT("2026-09-01T07:51:06.288426+00:00"), updated_at=DT("2026-09-01T08:38:17.129588+00:00")),
            BusinessRecord(id=47151, module="task", serial_no="RW202609011551063635829810", title="立案登记—SHMS2600438", customer="测试555", status="待接收", owner="fwl", department="调查取证部", description="完成法院立案信息登记并上传受理材料", data={"deadline": "2026-09-08", "priority": "普通", "source": "案件任务", "creation_mode": "自动", "task_type": "固定任务", "fixed_task_key": "filing-registration", "initiator": "system", "collaborators": [], "case_no": "SHMS2600438", "case_id": 47150, "case_stage": "立案", "system_created_by": "system"}, created_at=DT("2026-09-01T07:51:06.288426+00:00"), updated_at=DT("2026-09-01T07:51:06.288426+00:00")),
            BusinessRecord(id=47152, module="task", serial_no="RW202609011551063710622E3D", title="送达跟踪—SHMS2600438", customer="测试555", status="待接收", owner="fwl", department="调查取证部", description="跟踪法院送达情况并记录送达结果", data={"deadline": "2026-09-15", "priority": "普通", "source": "案件任务", "creation_mode": "自动", "task_type": "固定任务", "fixed_task_key": "service-tracking", "initiator": "system", "collaborators": [], "case_no": "SHMS2600438", "case_id": 47150, "case_stage": "立案", "system_created_by": "system"}, created_at=DT("2026-09-01T07:51:06.288426+00:00"), updated_at=DT("2026-09-01T07:51:06.288426+00:00")),
        ])
        event_rows = [
            (4399, 4111, "创建调查中心记录", "", "草稿", "fwl", "类型：clue", "2026-08-17T02:28:14.936658+00:00"),
            (4400, 4111, "提交线索审批", "草稿", "待审批", "fwl", "提交线索审批", "2026-08-17T02:28:14.972873+00:00"),
            (4485, 4111, "线索审批通过", "待审批", "待取证", "admin", "11", "2026-08-18T05:42:51.038284+00:00"),
            (4750, 4111, "上传调查材料", "待取证", "待取证", "admin", "取证文件：SHMS2600436-结算提成表-20260901130504.docx", "2026-09-01T07:50:39.276638+00:00"),
            (4751, 47149, "登记线索取证证据", "", "已取证", "admin", "来源线索 M26085930", "2026-09-01T07:50:39.357305+00:00"),
            (4752, 4111, "登记线索取证", "待取证", "已取证", "admin", "取证日期 2026-09-01；取证机构 上海市东方公证处；公证书号 1111；取证文件 1 个。", "2026-09-01T07:50:39.357305+00:00"),
            (4753, 4111, "已取证线索生成案件", "已取证", "已转案件", "admin", "生成案件 SHMS2600438", "2026-09-01T07:51:06.288426+00:00"),
            (4754, 47150, "线索生成案件", "", "等待公证书", "admin", "来源线索 M26085930 / 来源任务合同 未关联合同；案由 侵害商标权纠纷 / 经办律师 范文林 / 律师助理 范文林", "2026-09-01T07:51:06.288426+00:00"),
            (4755, 47151, "生成案件固定任务", "", "待接收", "system", "案件 SHMS2600438 创建时自动生成", "2026-09-01T07:51:06.288426+00:00"),
            (4756, 47152, "生成案件固定任务", "", "待接收", "system", "案件 SHMS2600438 创建时自动生成", "2026-09-01T07:51:06.288426+00:00"),
            (4761, 47150, "案件被复制", "等待公证书", "等待公证书", "admin", "新案件：SHMS2600438A", "2026-09-01T08:37:10.294018+00:00"),
            (4762, 47150, "修改开庭律师", "等待公证书", "等待公证书", "admin", "开庭律师：未设置 → 范文林", "2026-09-01T08:37:36.386005+00:00"),
            (4763, 47150, "修改开庭律师", "等待公证书", "等待公证书", "admin", "开庭律师：范文林 → 陶国南", "2026-09-01T08:37:54.153340+00:00"),
            (4764, 47150, "修改法院信息", "等待公证书", "等待公证书", "admin", "修改一审法院信息", "2026-09-01T08:38:17.129588+00:00"),
        ]
        db.add_all([WorkflowEvent(id=i, record_id=r, action=a, from_status=f, to_status=t, operator=o, comment=c, created_at=DT(d)) for i, r, a, f, t, o, c, d in event_rows])
        db.add(FileAttachment(id=668, record_id=4111, category="取证文件", original_name="SHMS2600436-结算提成表-20260901130504.docx", stored_name="row4-original-668.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=36962, path=upload_path, uploader="admin", remark="线索取证登记附件", created_at=DT("2026-09-01T07:50:39.276638+00:00")))
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
