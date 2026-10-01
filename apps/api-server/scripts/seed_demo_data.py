"""显式开发环境示例数据初始化；生产镜像不包含此脚本。"""

import asyncio
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import func, select

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings
from app.core.constants import CONTRACT_APPROVED_STATUS
from app.core.lifecycle import _backfill_clue_generated_case_register_dates, _upgrade_schema
from app.core.startup_data import initialize_startup_data
from app.core.startup_migrations import lock_startup_transaction, migrate_startup_schema
from app.database import SessionLocal, engine
from app.models import (
    BusinessRecord, ContractApprovalStep, DocumentTemplate, HearingSchedule,
    ReceivablePlan, SealAsset, WorkflowEvent,
)


def _seed_business_records() -> list[BusinessRecord]:
    rows = [
        ("customer", "KH20260714001", "光明乳业股份有限公司", "光明乳业股份有限公司", "正常", "朱菁芸", {"contact": "法务部", "phone": "021-12345678", "level": "重点客户"}),
        ("customer", "KH20260714002", "萨普托乳业（中国）有限公司", "萨普托乳业（中国）有限公司", "跟进中", "朱淑旖", {"contact": "品牌保护部", "phone": "021-87654321", "level": "重点客户"}),
        ("contract", "HT2026070018", "知识产权维权专项法律服务合同", "迈大食品（上海）有限公司", "审批中", "陈名涛", {"amount": "280000.00", "signed_at": "2026-07-08", "type": "专项服务"}),
        ("contract", "HT2026060097", "常年法律顾问合同", "上海天路人造草坪有限公司", CONTRACT_APPROVED_STATUS, "陶勇刚", {"amount": "120000.00", "signed_at": "2026-06-20", "type": "法律顾问"}),
        ("case", "SH191000382B", "光明乳业商标侵权纠纷", "光明乳业股份有限公司", "文书准备", "陈名涛", {"court": "上海市宝山区人民法院", "case_type": "民事案件", "opponent": "安徽鑫牛食品有限公司"}),
        ("case", "SHMS2600387", "龙角散商标侵权纠纷", "株式会社龙角散", "一审立案受理", "陶勇刚", {"court": "杭州市余杭区人民法院", "case_type": "民事案件", "opponent": "杭州取道贸易有限公司"}),
        ("task", "RW20260714001", "准备开庭代理词及证据目录", "上海天路人造草坪有限公司", "处理中", "陶勇刚", {"deadline": "2026-07-15", "priority": "紧急", "source": "案件任务"}),
        ("task", "RW20260714002", "审核合同付款节点", "迈大食品（上海）有限公司", "待处理", "朱淑旖", {"deadline": "2026-07-17", "priority": "普通", "source": "合同任务"}),
        ("clue", "XS2026070015", "线上店铺销售疑似侵权产品", "北京汇源食品饮料有限公司", "待审批", "卢愿", {"platform": "淘宝", "product": "果汁饮料", "notary": "待申请"}),
        ("seal", "YY2026070042", "民事起诉状用印申请", "株式会社龙角散", "待审批", "陶勇刚", {"seal_type": "公章", "copies": 3, "purpose": "法院立案"}),
        ("finance", "FY2026070093", "上海市宝山区人民法院诉讼费", "光明乳业股份有限公司", "待审批", "陈名涛", {"amount": "3500.00", "fee_type": "官方费用", "case_no": "SH191000382B"}),
        ("document", "SW2026070031", "上海市徐汇区人民法院开庭传票", "上海益民食品一厂有限公司", "已签收", "江彤", {"direction": "收文", "received_at": "2026-07-14", "case_no": "SHMS2200026"}),
    ]
    return [BusinessRecord(module=m, serial_no=no, title=title, customer=customer, status=st, owner=owner, data=data) for m, no, title, customer, st, owner, data in rows]


async def seed_demo_data(db) -> None:
    """只在显式命令中补齐既有示例记录。"""
    record_count = await db.scalar(select(func.count()).select_from(BusinessRecord))
    if not record_count:
        db.add_all(_seed_business_records())
        await db.flush()
    records = (await db.scalars(select(BusinessRecord))).all()
    original_customer = next(
        (record for record in records if record.module == "customer" and record.serial_no == "SHKH1810649"),
        None,
    )
    if original_customer is None:
        original_customer = BusinessRecord(
            module="customer", serial_no="SHKH1810649", title="test", customer="test",
            status="正常", owner="admin", department="上海分所",
            data={
                "source_person": "管理者", "customer_managers": ["管理者"],
                "customer_type": "客户", "invoice_address": "test",
                "customer_source": "管理者", "is_shared": "否",
                "level": "立案客户", "is_assisted": "否",
                "file_date": "2018-07-29", "last_contact_at": "2018-07-29",
                "last_modified_date": "2018-07-29", "contact_count": 0,
                "contract_count": 3, "civil_case_count": 2,
                "agency_fee_due": 0, "official_fee_unreceived": -4000,
            },
        )
        db.add(original_customer)
        await db.flush()
        records.append(original_customer)
    elif original_customer.title == "test" and (original_customer.data or {}).get("source_person") == "管理者":
        # 仅补齐系统示例客户的缺失字段，不覆盖用户填写的值。
        fixture_defaults = {
            "customer_type": "客户", "invoice_address": "test",
            "customer_source": "管理者", "is_shared": "否",
            "level": "立案客户", "is_assisted": "否",
        }
        fixture_data = dict(original_customer.data or {})
        for key, value in fixture_defaults.items():
            if not fixture_data.get(key):
                fixture_data[key] = value
        original_customer.data = fixture_data
    original_contracts = [
        ("SHHT2610035", "test_合同", "审批中", {"contract_body": "律所"}),
        ("SHHT2510026", "test_合同", "审批中", {
            "contract_body": "律所", "official_paid": 0, "official_received": 4000,
            "official_unreceived": -4000, "official_loss": 0, "agency_total": 6000,
            "agency_received": 6000, "agency_due": 0, "other_total": 0,
            "other_paid": 0, "other_due": 0, "invoice_opened": 0,
            "invoice_should": 6000, "invoice_excess": 0,
        }),
        ("SHHT1810328", "test_合同", "已归档", {"contract_body": "律所"}),
    ]
    existing_contract_nos = {record.serial_no for record in records if record.module == "contract"}
    for serial_no, title, contract_status, data in original_contracts:
        if serial_no in existing_contract_nos:
            continue
        original_contract = BusinessRecord(
            module="contract", serial_no=serial_no, title=title, customer="test",
            status=contract_status, owner="admin", department="上海分所",
            data={
                "type": "争议解决合同", "fee_type": "固定收费", "signed_at": "",
                "source_person": "管理者", "amount": data.get("agency_total", 0),
                "official_paid": 0, "official_received": 0, "official_unreceived": 0,
                "official_loss": 0, "agency_total": 0, "agency_received": 0,
                "agency_due": 0, "other_total": 0, "other_paid": 0,
                "other_due": 0, "invoice_opened": 0, "invoice_should": 0,
                "invoice_excess": 0, **data,
            },
        )
        db.add(original_contract)
        await db.flush()
        records.append(original_contract)
    original_cases = [
        ("SHMS2300502", "一审待客户回款", "上海台享餐饮管理有限公司", "长寿区娅娅小吃店", "重庆市自由贸易试验区人民法院", "（2023）渝0192民初10300号", "外部合作律师", "外部合作律师", "2023-12-29", 928, "结算规档任务", "本案SHMS2300502已到账超过30日,请尽快提交结算并归档.", "外部合作律师", "2025-09-26"),
        ("SHMS2400031", "一审判决结案", "中饮巴比食品股份有限公司", "高新区芭比特包包子铺", "成都高新技术产业开发区人民法院", "(2024)川0191民初18219号", "System", "刘波", "2026-02-12", 152, "结算规档任务", "本案SHMS2400031已到账超过30日,请尽快提交结算并归档.", "刘波", "2026-03-25"),
        ("SHMS2400065", "一审判决结案", "中饮巴比食品股份有限公司", "璧山区段世华面馆", "重庆市自由贸易试验区人民法院", "(2024)渝0192民初10299号", "System", "刘波", "2026-02-12", 152, "结算规档任务", "本案SHMS2400065已到账超过30日,请尽快提交结算并归档.", "刘波", "2026-03-25"),
        ("SHMS2500709A", "已归档", "上海天路人造草坪有限公司", "常州莱因人造草坪科技有限公司", "江苏省苏州市中级人民法院", "（2025）苏05民初1478号", "陶勇刚", "陶勇刚", "2026-07-08", 6, "结算归档一审和解结案", "结算归档", "陶亮", "2026-05-23"),
        ("SHMS2400317", "等待公证书", "珠海双喜电器股份有限公司", "义乌市热康日用品厂", "", "", "System", "", "2024-05-19", 786, "案件审核", "品管回复停止取证", "System", "2026-07-15"),
        ("SH171000067", "一审待客户回款", "珠海格力电器股份有限公司", "常州市天宁区天宁正和电子经营部", "常州市天宁区人民法院", "（2018）苏0402民初4642号", "崔铧尹", "李晓岩,朱莹", "2023-03-15", 1217, "案件跟进回款", "这几个格力案件，现在什么情况？", "陶国南", "2026-07-16"),
        ("SH171000093", "一审待客户回款", "珠海格力电器股份有限公司", "常州市钱达电器经营部", "常州市天宁区人民法院", "（2018）苏0402民初4643号", "崔铧尹", "李晓岩,朱莹", "2023-02-13", 1247, "案件跟进回款", "这几个格力案件，现在什么情况？", "陶国南", "2026-07-16"),
        ("SHMS2500647", "文书准备", "九牧王股份有限公司", "亳州市谯城区衣家园服装批发店（个体工商户）", "利辛县人民法院", "", "李佳妮", "张美莹", "2026-01-07", 188, "案件审核", "", "李佳妮", "2026-07-16"),
        ("SH191000297", "执行终本", "中粮集团有限公司", "上海联华快客便利有限公司习勤店,蓬莱华夏葡园酒业有限公司,上海联华快客便利有限公司", "上海市徐汇区人民法院", "（2024）沪0104执7123号、（2025）沪0104执异495号", "陶勇刚", "李佳妮", "2025-11-24", 232, "终本案件，先到账的先结算发提成，后面还要继续追讨", "", "审核管理（赵媛）", "2026-07-16"),
        ("SHMS2500149", "文书准备", "广东三雄极光照明股份有限公司", "王勇,上海寻梦信息技术有限公司", "上海市长宁区人民法院", "", "王晓英", "郝蕴", "2025-08-13", 335, "文书审核", "已修改上传系统，是否可以盖章", "郝蕴", "2026-07-16"),
    ]
    existing_case_nos = {record.serial_no for record in records if record.module == "case"}
    for case_item in original_cases:
        serial_no, case_status, plaintiff, defendant, court, court_case_no, lawyer, assistant, changed_at, days, task_name, task_content, task_handler, task_time = case_item
        if serial_no in existing_case_nos:
            continue
        original_case = BusinessRecord(
            module="case", serial_no=serial_no, title=f"{plaintiff}诉{defendant}", customer=plaintiff,
            status=case_status, owner="admin", department="上海分所",
            data={"case_type": "民事案件", "plaintiff": plaintiff, "opponent": defendant,
                  "court": court, "court_case_no": court_case_no, "hearing_lawyer": lawyer,
                  "handling_lawyers": [lawyer] if lawyer else [], "assistant": assistant,
                  "phase_changed_at": changed_at, "phase_days": days, "task_name": task_name,
                  "task_content": task_content, "task_handler": task_handler, "task_time": task_time},
        )
        db.add(original_case); await db.flush(); records.append(original_case)
    event_record_ids = set((await db.scalars(select(WorkflowEvent.record_id).distinct())).all())
    for record in records:
        if record.id not in event_record_ids:
            db.add(WorkflowEvent(record_id=record.id, action="系统初始化", to_status=record.status, operator="system", comment="初始化示例业务数据"))
    if not await db.scalar(select(func.count()).select_from(ReceivablePlan)):
        contracts = {record.serial_no: record for record in records if record.module == "contract"}
        if contracts.get("HT2026070018"):
            db.add_all([
                ReceivablePlan(contract_record_id=contracts["HT2026070018"].id, phase="合同签订首付款", due_date=date(2026, 7, 20), amount=140000, received_amount=0, status="待收款", payer=contracts["HT2026070018"].customer),
                ReceivablePlan(contract_record_id=contracts["HT2026070018"].id, phase="项目办结尾款", due_date=date(2026, 12, 20), amount=140000, received_amount=0, status="待收款", payer=contracts["HT2026070018"].customer),
            ])
        if contracts.get("HT2026060097"):
            db.add(ReceivablePlan(contract_record_id=contracts["HT2026060097"].id, phase="年度顾问费", due_date=date(2026, 6, 30), amount=120000, received_amount=80000, status="部分收款", payer=contracts["HT2026060097"].customer))
    if not await db.scalar(select(func.count()).select_from(HearingSchedule)):
        cases = {record.serial_no: record for record in records if record.module == "case"}
        if cases.get("SH191000382B"):
            db.add(HearingSchedule(case_record_id=cases["SH191000382B"].id, hearing_date=date(2026, 7, 15), hearing_time="09:00", court="上海市宝山区人民法院", courtroom="第六法庭", hearing_type="一审开庭", hearing_lawyer="陈名涛"))
        if cases.get("SHMS2600387"):
            db.add(HearingSchedule(case_record_id=cases["SHMS2600387"].id, hearing_date=date(2026, 7, 20), hearing_time="14:00", court="杭州市余杭区人民法院", courtroom="第二法庭", hearing_type="证据交换", hearing_lawyer="陶勇刚"))
    if not await db.scalar(select(func.count()).select_from(DocumentTemplate)):
        db.add_all([
            DocumentTemplate(name="民事起诉状", category="诉讼文书", version="2026.1", description="知识产权民事案件起诉状标准模板", fields=["原告", "被告", "诉讼请求", "事实与理由"]),
            DocumentTemplate(name="律师函", category="非诉文书", version="2026.1", description="侵权告知及停止侵权律师函", fields=["委托人", "收函人", "事实", "法律意见"]),
            DocumentTemplate(name="案件归档目录", category="归档文书", version="2026.1", description="案件归档材料目录标准模板", fields=["案号", "客户", "材料清单", "归档日期"]),
        ])
    await db.flush()
    assets_by_type = {item.seal_type: item for item in (await db.scalars(select(SealAsset))).all()}
    for record in records:
        if record.module == "seal" and not (record.data or {}).get("seal_asset_id"):
            asset = assets_by_type.get((record.data or {}).get("seal_type")) or assets_by_type.get("公章")
            if asset:
                record.data = {**(record.data or {}), "seal_asset_id": asset.id, "seal_name": asset.name}
    approval_contracts = [record for record in records if record.module == "contract" and record.status == "审批中"]
    for contract in approval_contracts:
        if not await db.scalar(select(func.count()).select_from(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract.id)):
            db.add(ContractApprovalStep(contract_record_id=contract.id, step_order=1, approver="admin", status="待审批", comment="历史合同补充默认审批节点"))


async def main() -> None:
    if settings.app_env.strip().lower() != "development":
        raise RuntimeError("示例数据只能在 development 环境显式初始化")
    if not settings.seed_demo_data:
        raise RuntimeError("显式初始化示例数据前必须设置 SEED_DEMO_DATA=true")
    try:
        await migrate_startup_schema(engine, _upgrade_schema)
        await initialize_startup_data(SessionLocal, _backfill_clue_generated_case_register_dates)
        async with SessionLocal() as db:
            await lock_startup_transaction(await db.connection())
            await seed_demo_data(db)
            await db.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
