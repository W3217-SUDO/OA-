"""案件模板字段投影，只读取有明确关系的案件、线索与到账来源。"""

from fastapi import HTTPException
from sqlalchemy import select

from app.models import BusinessRecord, SystemParameter, User


CIVIL_HEADERS = [
    "案件编号", "案由", "原告", "被告", "案件阶段", "法院名称", "开庭时间", "经办律师", "律师助理", "客戶管理人",
    "线索号", "证书号", "证物存放处", "一审法院", "一审法院号", "二审法院", "二审法院号", "再审法院", "再审法院号",
    "归档号", "店铺名称", "店铺Id", "销量",
]
HANDOVER_HEADERS = [
    "序号", "合同编号", "案件编号", "原告", "被告", "归档号/阶段", "案由", "律师助理", "经办律师",
    "到账日期", "账号", "到账名称", "到账总金额", "律师费", "备注", "提交日期",
]


def case_value(data: dict, *keys: str, legacy: str = "") -> str:
    for key in keys:
        value = data.get(key)
        if value is not None and value != "" and value != []:
            return ",".join(str(item) for item in value) if isinstance(value, list) else str(value)
    snapshot = data.get("legacy_record")
    if legacy and isinstance(snapshot, dict) and snapshot.get(legacy) is not None:
        return str(snapshot[legacy])
    return ""


def _people(value: str, users: dict) -> str:
    return ",".join(users.get(part.strip(), part.strip()) for part in value.replace("、", ",").split(",") if part.strip())


def _court_name(value: str, names_by_code: dict[str, str], case_no: str) -> str:
    value = value.strip()
    if not value:
        return ""
    name = names_by_code.get(value.casefold())
    if name:
        return name
    # 代码只能由权威参数解析；历史名称字段中的中文法院全称保持原值。
    is_saved_name = value in names_by_code.values() or (
        any("\u4e00" <= char <= "\u9fff" for char in value)
        and value.endswith(("法院", "法庭", "仲裁委员会"))
    )
    if value.casefold() not in names_by_code and is_saved_name:
        return value
    raise HTTPException(422, f"案件 {case_no} 的法院代码或名称 {value} 无法解析，请先完善法院参数")


async def case_export_projections(records, identity: dict, db, *, include_courts: bool = True) -> list[dict]:
    from app.core.permissions import _record_scope_conditions
    from app.core.query_batches import _scalars_in_batches
    from app.core.system import _dashboard_people

    scope = await _record_scope_conditions(identity, db)
    loaded_users = list((await db.scalars(select(User))).all())
    users = {user.username: user.display_name for user in loaded_users}
    users_by_username = {user.username.lower(): user for user in loaded_users}
    # 历史案件也需要解析已停用法院的名称，不改变新建案件的可选范围。
    courts = (await db.scalars(select(SystemParameter).where(SystemParameter.category == "court"))).all() if include_courts else []
    court_names = {str(court.code).strip().casefold(): str(court.name or "").strip() for court in courts}
    customer_refs = {record.id: int((record.data or {}).get("customer_id") or (record.data or {}).get("customer_record_id") or 0) for record in records}
    customers_by_id = {item.id: item for item in await _scalars_in_batches(
        db, {customer_id for customer_id in customer_refs.values() if customer_id},
        lambda batch: select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.id.in_(batch), *scope),
    )}
    clue_refs = []
    for record in records:
        data = record.data or {}
        clue_no = case_value(data, "investigation_clue_nos", "clue_no", "investigation_clue", "source_clue_no", legacy="InvestigationClueNos")
        first_clue_no = clue_no.replace("、", ",").split(",")[0].strip()
        clue_id = int(data.get("clue_record_id") or data.get("investigation_clue_id") or 0)
        clue_refs.append((clue_no, first_clue_no, clue_id))
    clues_by_no = {item.serial_no: item for item in await _scalars_in_batches(
        db, {ref[1] for ref in clue_refs if ref[1]},
        lambda batch: select(BusinessRecord).where(BusinessRecord.module == "clue", BusinessRecord.serial_no.in_(batch), *scope),
    )}
    clues_by_id = {item.id: item for item in await _scalars_in_batches(
        db, {ref[2] for ref in clue_refs if not ref[1] and ref[2]},
        lambda batch: select(BusinessRecord).where(BusinessRecord.module == "clue", BusinessRecord.id.in_(batch), *scope),
    )}
    projections = []
    for record, (clue_no, first_clue_no, clue_id) in zip(records, clue_refs, strict=True):
        data = record.data or {}
        clue = clues_by_no.get(first_clue_no) if first_clue_no else clues_by_id.get(clue_id)
        clue_data = clue.data or {} if clue else {}
        customer = customers_by_id.get(customer_refs[record.id])
        customer_data = customer.data or {} if customer else {}
        customer_legacy = customer_data.get("legacy_record") if isinstance(customer_data.get("legacy_record"), dict) else {}
        product = clue_data.get("product") if isinstance(clue_data.get("product"), dict) else {}
        projection = {
            "case_no": record.serial_no,
            "cause": case_value(data, "cause_or_charge", "cause", legacy="CauseName"),
            "plaintiff": case_value(data, "plaintiff", "plaintiffs", legacy="AppellantNames"),
            "defendant": case_value(data, "opponent", "defendant", "defendants", legacy="AppelleeNames"),
            "stage": case_value(data, "case_phase_name", legacy="CasePhaseName") or record.status,
            "hearing_date": case_value(data, "first_court_hearing_date", "first_instance_lawful_day", "hearing_date", legacy="FirstIntanceLawfulDay"),
            "lawyer": _people(case_value(data, "handling_lawyers", "handling_lawyer", legacy="CaseLawyerName"), users),
            "assistant": _people(case_value(data, "assistant", "case_assistant", legacy="CaseAssistantName"), users),
            "court_lawyer": _people(case_value(data, "hearing_lawyer", "court_lawyer", legacy="CourtLawyerName"), users),
            "business_owner": _people(case_value(data, "business_owner_display_name", "business_owner", "source_person", legacy="BusinessOwnerName"), users),
            "brand_managers": _dashboard_people(users_by_username, customer_data.get("customer_managers"), customer_legacy.get("CoordinatorName")),
            "clue_no": clue_no,
            "notary_no": case_value(data, "notary_nos", "notary_no", legacy="NotarialNos"),
            "deposit_address": case_value(data, "deposit_address", "evidence_location", legacy="DepositAddress"),
            "first_case_no": case_value(data, "first_court_case_no", "first_instance_case_no", "court_case_no", legacy="FirstIntanceCaseNo"),
            "second_case_no": case_value(data, "second_court_case_no", "second_instance_case_no", legacy="SecondIntanceCaseNo"),
            "retrial_case_no": case_value(data, "retrial_court_case_no", "retrial_case_no", "last_instance_case_no", legacy="LastIntanceCaseNo"),
            "archive_no": case_value(data, "archive_no", "file_no", legacy="FileNo"),
            "shop_name": case_value(clue_data, "shop_name", "store_name", legacy="StoreName"),
            "shop_id": case_value(clue_data, "shop_id", "store_id", legacy="StoreId"),
            "sales": case_value(product, "sale_num", "SaleNum") or case_value(clue_data, "sales", "sale_num", "sales_volume", legacy="SaleNum"),
            "contract_no": case_value(data, "contract_no", legacy="ContractNo"),
        }
        if include_courts:
            projection.update({
                "first_court": _court_name(case_value(data, "first_court_name", "first_instance_court", "court", legacy="FirstIntanceCourtName"), court_names, record.serial_no),
                "second_court": _court_name(case_value(data, "second_court_name", "second_instance_court", legacy="SecondIntanceCourtName"), court_names, record.serial_no),
                "retrial_court": _court_name(case_value(data, "retrial_court_name", "last_instance_court", legacy="LastIntanceCourtName"), court_names, record.serial_no),
            })
        projections.append(projection)
    return projections


def civil_export_rows(projections: list[dict]) -> list[list[str]]:
    fields = ["case_no", "cause", "plaintiff", "defendant", "stage", "first_court", "hearing_date", "lawyer", "assistant",
              "business_owner", "clue_no", "notary_no", "deposit_address", "first_court", "first_case_no", "second_court",
              "second_case_no", "retrial_court", "retrial_case_no", "archive_no", "shop_name", "shop_id", "sales"]
    return [[item[key] for key in fields] for item in projections]
