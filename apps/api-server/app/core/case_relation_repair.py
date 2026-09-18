"""按明确业务编号修复已确认的历史案件关系，不猜测其他数据。"""
from sqlalchemy import select
from app.models import BusinessRecord, WorkflowEvent
from app.core.case_relations import case_clues
from app.core.contracts import _resolve_clue_source_contract
from app.core.case_merge import merge_case_relations, move_case_finance_files


async def repair_case_relations(spec, db):
    identity = {"username": "case-relation-repair", "role": "admin"}
    for number in spec.get("source_contract_cases", []):
        case = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == number))
        if case is None:
            raise ValueError(f"指定案件不存在：{number}")
        if (case.data or {}).get("contract_no"):
            continue
        contracts = {}
        for clue in await case_clues(case, db):
            contract, reason = await _resolve_clue_source_contract(clue, identity, db)
            if contract is None:
                raise ValueError(reason)
            contracts[contract.id] = contract
            investigation_no = str((clue.data or {}).get("investigation_no") or "")
            if investigation_no:
                investigation = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "investigation", BusinessRecord.serial_no == investigation_no, BusinessRecord.customer == case.customer))
                if investigation is None:
                    raise ValueError("来源调查编号无有效对应记录")
                clue.data = {**clue.data, "investigation_record_id": investigation.id}
                investigation.data = {**investigation.data, "contract_id": contract.id, "contract_record_id": contract.id}
        if len(contracts) != 1:
            raise ValueError("来源合同必须唯一")
        contract = next(iter(contracts.values()))
        case.data = {**case.data, "contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract.serial_no}
        db.add(WorkflowEvent(record_id=case.id, action="修复来源合同关联", from_status=case.status,
            to_status=case.status, operator=identity["username"], comment=f"来源线索对应合同：{contract.serial_no}"))
    for pair in spec.get("existing_merges", []):
        source = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == pair["source"]))
        target = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == pair["target"]))
        if not source or not target or source.customer != target.customer or source.status != "已合并" or (source.data or {}).get("merged_into_case_no") != target.serial_no:
            raise ValueError("历史合并关系与指定修复范围不符")
        await merge_case_relations(source, target, db)
        await move_case_finance_files(source, target, identity, db)

    for reference in spec.get("fee_contracts", []):
        fee = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "finance", BusinessRecord.serial_no == reference["fee_no"]))
        contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "contract", BusinessRecord.serial_no == reference["contract_no"]))
        if fee is None or contract is None or fee.customer != contract.customer or (fee.data or {}).get("contract_no") != contract.serial_no:
            raise ValueError("费用合同修复范围与权威编号不符")
        data = fee.data or {}
        if data.get("contract_id") == contract.id and data.get("contract_record_id") == contract.id:
            continue
        for key in ("contract_id", "contract_record_id"):
            previous = await db.get(BusinessRecord, int(data[key])) if data.get(key) else None
            if previous and previous.module == "contract" and previous.id != contract.id:
                raise ValueError("费用合同ID与编号指向不同有效合同，停止修复")
        fee.data = {**data, "contract_id": contract.id, "contract_record_id": contract.id}
        db.add(WorkflowEvent(record_id=fee.id, action="修复费用合同关联", from_status=fee.status,
            to_status=fee.status, operator=identity["username"], comment=contract.serial_no))
