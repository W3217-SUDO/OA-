from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ARCHIVE = Path(r"D:\OA系统源码归档_20260717")
METADATA = ARCHIVE / "database-metadata" / "oa-db-metadata.json"
STATUS = ARCHIVE / "database-status" / "oa-db-status-distributions.json"
OUT = ARCHIVE / "analysis"


MODULES = [
    {
        "module": "客户管理",
        "areas": "CRM",
        "controllers": "Customer; CustomerContacts; CustomerFile; CustomerShare; CustomerAssignment; Communication",
        "tables": "CRM_Customer; CRM_Customer_Contacts; CRM_Customer_File; CRM_Customer_Share; CRM_Communication",
        "pages": "客户列表/公海/回收站/共享/最近联系/最近更新/利益冲突检索/详情/编辑",
        "lifecycle": "建档→分配管理人→联系与共享→签约；删除进入回收站，恢复或释放进入公海",
        "links": "为合同、案件、调查、用印、发票提供客户主体",
    },
    {
        "module": "合同中心",
        "areas": "CMS; FCM",
        "controllers": "Contract; ContractDraft; ContractAudit; ContractArchive; ContractFile; ContractPayment; GL; AR",
        "tables": "FCM_Contract; FCM_Contract_Audit; FCM_Contract_File; FCM_Contract_Object; FCM_Contract_Payment",
        "pages": "草稿/待提交/审批中/已通过/已驳回/总账/归档/文件",
        "lifecycle": "草稿→提交审批→审批通过或驳回→履行/建案/开票→归档",
        "links": "上接客户，下接案件、用印、应收和发票",
    },
    {
        "module": "案件中心",
        "areas": "Legal; Lawsuit; IPR",
        "controllers": "Case; CaseList; CaseFile; CaseTask; CasePhase; CaseArchive; Litigant",
        "tables": "Legal_Case; Legal_Case_File; Legal_Case_Task; Legal_Case_Task_Node; Legal_Case_Archive; Legal_Case_Litigant",
        "pages": "新建/详情/当事人/司法机关/律师分配/阶段/执行/排期/文件/任务/归档",
        "lifecycle": "合同或线索建案→补全当事人和司法机关→分配律师→阶段推进→任务/排期/费用→结案归档",
        "links": "连接客户、合同、线索、任务、文件、财务、用印和归档",
    },
    {
        "module": "协同任务",
        "areas": "TP; Legal",
        "controllers": "Task; TaskNode; TaskMessage; TaskFile; CaseTask",
        "tables": "Legal_Case_Task; Legal_Case_Task_Node; Legal_Case_Task_Message; Legal_Case_Task_File; Legal_Case_Task_Notification",
        "pages": "任务列表/消息/详情/发起/节点/交接/验收/重启",
        "lifecycle": "发起→接收/处理→节点协作→交接或拒绝/停止/撤回→完成→验收；完成后可重启",
        "links": "通常挂接案件，可跨人员和部门协作",
    },
    {
        "module": "调查与取证",
        "areas": "CIT",
        "controllers": "Investigation; InvestigationTask; InvestigationClue; InvestigationClueAudit; InvestigationClueEvidence",
        "tables": "Legal_Investigation; Legal_Investigation_Task; Legal_Investigation_Clue; Legal_Investigation_Clue_Audit; Legal_Investigation_Clue_Evidence",
        "pages": "调查项目/调查任务/线索/内审/客户审核/证据/公证/线索转案件",
        "lifecycle": "调查立项→任务→线索提交→内部审核→客户审核→取证→证据入库/出库/销毁→生成或合并案件",
        "links": "上接合同或客户，下接案件、证据、公证和费用",
    },
    {
        "module": "用印管理（独立模块）",
        "areas": "AWS",
        "controllers": "OfficialDocument; OfficialDocumentAudit; OfficialDocumentFile",
        "tables": "AWS_OfficialDocument; AWS_OfficialDocument_Audit; AWS_OfficialDocument_File",
        "pages": "用印申请/待审核/已通过/已拒绝/预览/文件/标记用印/下载",
        "lifecycle": "创建申请→提交审核→通过或拒绝→待用印→标记已用印；可撤回或终止",
        "links": "自身独立编号、审批、文件和打印状态；可选关联合同号或案号",
    },
    {
        "module": "财务中心",
        "areas": "FAM; FAS; FSC; FIO",
        "controllers": "AR; AP; CaseFee; InternalFee; Invoice; InvoiceAudit; Payment; PaymentAudit; PaymentPacking; Settlement; ArchiveSettlement",
        "tables": "FAM_AR_Payment; FAM_AP_Payment; FAM_InternalFee; FAM_InternalFee_Payment; FAM_Invoice; FAM_Payment_Packing",
        "pages": "应收/回款/案件费用/内部费用/请款审批/付款打包/发票/结算/归档结算",
        "lifecycle": "案件或合同产生费用→应收/内部请款→审批→开票或付款→回款匹配→结算审核→支付/退回→归档结算",
        "links": "与客户、合同、案件、费用明细、银行回款、发票和归档联动",
    },
    {
        "module": "人事与权限",
        "areas": "HR; System; Account",
        "controllers": "Staff; Department; Role; User; SystemManagement; SystemCenter",
        "tables": "HR_Staff; HR_Department; HR_Role; SYS_User; SYS_Role; SYS_Menu; SYS_Log",
        "pages": "员工/部门/角色/账号/密码/绩效/离岗/权限/系统日志",
        "lifecycle": "员工建档→账号与角色→部门/岗位→菜单和数据范围→离岗停用",
        "links": "为全部业务提供操作人、审批人、负责人和数据权限",
    },
    {
        "module": "仓库与证物",
        "areas": "WMS; CIT",
        "controllers": "Warehouse; WarehouseStorageLocation; InvestigationClueEvidence",
        "tables": "BAS_Warehouse; WMS_Warehouse; WMS_Warehouse_StorageLocation; Legal_Investigation_Clue_Evidence",
        "pages": "仓库/库位/证物入库/领取出库/重新入库/销毁",
        "lifecycle": "未入库→已入库→待领取→已出库→重新入库或销毁",
        "links": "证物来自调查线索，并保留仓库和流转状态",
    },
    {
        "module": "报表与控制台",
        "areas": "RPT; BAS",
        "controllers": "Report; Home; Dashboard",
        "tables": "跨模块视图与聚合查询",
        "pages": "控制台、待办、案件趋势、开庭排期、业务报表",
        "lifecycle": "只读聚合与钻取，不应创建独立业务真相",
        "links": "汇总任务、案件、合同、客户和财务数据",
    },
]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    metadata = json.loads(METADATA.read_text(encoding="utf-8-sig"))
    status = json.loads(STATUS.read_text(encoding="utf-8-sig"))
    OUT.mkdir(parents=True, exist_ok=True)

    write_csv(
        OUT / "数据库表清单.csv",
        metadata["tables"],
        ["schema_name", "table_name", "row_count"],
    )
    write_csv(
        OUT / "数据库状态分布.csv",
        status["status_distributions"],
        ["entity", "field", "value", "count"],
    )
    procedure_rows = [
        {"schema_name": item["schema_name"], "procedure_name": item["procedure_name"]}
        for item in metadata["procedures"]
    ]
    write_csv(
        OUT / "存储过程名称清单.csv",
        procedure_rows,
        ["schema_name", "procedure_name"],
    )
    write_csv(
        OUT / "业务模块页面代码数据库对应表.csv",
        MODULES,
        ["module", "areas", "controllers", "tables", "pages", "lifecycle", "links"],
    )

    counts = {
        "tables": len(metadata["tables"]),
        "columns": len(metadata["columns"]),
        "foreign_keys": len(metadata["foreign_keys"]),
        "views": len(metadata["views"]),
        "procedures": len(metadata["procedures"]),
        "indexes": len(metadata["indexes"]),
        "status_rows": len(status["status_distributions"]),
    }
    (OUT / "盘点统计.json").write_text(
        json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    archive_files = [
        ARCHIVE / "oa-source-20260717.zip",
        ARCHIVE / "oa-db-metadata-20260717.zip",
        ARCHIVE / "oa-db-status-20260717.zip",
        ARCHIVE / "业务逻辑总览.md",
        ARCHIVE / "业务逻辑推断报告.md",
        ARCHIVE / "业务规则证据矩阵.csv",
        ARCHIVE / "原OA系统业务逻辑分析报告_20260717.docx",
        ARCHIVE / "律所管理系统业务蓝图确认稿_20260717.docx",
    ]
    manifest = []
    for path in archive_files:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        manifest.append(
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": digest.hexdigest().upper(),
            }
        )
    (ARCHIVE / "本地归档校验.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
