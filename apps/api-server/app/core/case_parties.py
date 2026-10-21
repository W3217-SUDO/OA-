"""案件当事人分类与既有诉讼字段投影；不创建或改写 CRM 客户。"""

from uuid import uuid4

from fastapi import HTTPException

from app.api_schemas.case_parties import ClassifiedCasePartyInput


PARTY_LABELS = {
    ("我方", "当事人", True): ("W_CLIENT", "我方客户（委托人）"),
    ("我方", "当事人", False): ("W_LITIGANT", "我方当事人（非委托人）"),
    ("我方", "关联方", False): ("W_AFFILIATE", "我方关联方"),
    ("我方", "第三人", False): ("W_THIRD", "我方第三人"),
    ("对方", "当事人", False): ("O_PARTY", "对方当事人"),
    ("对方", "第三人", False): ("O_THIRD", "对方第三人"),
}
MIRROR_POSITIONS = {"原告": "被告", "被告": "原告", "申请人": "被申请人", "被申请人": "申请人", "第三人": "第三人", "其他": "其他"}


def party_label(party: dict) -> str:
    return PARTY_LABELS[(party["party_standpoint"], party["party_type"], party["is_client_principal"])][1]


async def prepare_case_parties(record, values: list[ClassifiedCasePartyInput], identity: dict, db) -> dict:
    from app.core.crm import _customer_or_404

    if not values:
        raise HTTPException(422, "请至少录入一名我方当事人并关联委托客户")
    existing = {item["id"] for item in (record.data or {}).get("case_parties", []) if isinstance(item, dict) and item.get("id")}
    rows, seen_ids, seen_subjects = [], set(), set()
    clients = {}
    for value in values:
        row = value.model_dump()
        key = (row["party_standpoint"], row["party_type"], row["is_client_principal"])
        if key not in PARTY_LABELS:
            raise HTTPException(422, "当事人分类组合无效：关联方仅属于我方，委托人仅适用于我方当事人")
        row["name"] = row["name"].strip()
        row["credit_code"] = row["credit_code"].strip().upper()
        if not row["name"]:
            raise HTTPException(422, "请输入主体名称")
        if row["subject_kind"] == "法人" and (len(row["credit_code"]) != 18 or not row["credit_code"].isascii() or not row["credit_code"].isalnum()):
            raise HTTPException(422, f"{row['name']}：法人须填写18位统一社会信用代码")
        if row["party_type"] == "第三人" and row["litigation_status"] != "第三人":
            raise HTTPException(422, "第三人的诉讼地位必须为第三人")
        if row["party_type"] == "关联方" and row["litigation_status"] != "其他":
            raise HTTPException(422, "非本案当事人的关联方应选择其他诉讼地位")
        if row["id"] and row["id"] not in existing:
            raise HTTPException(409, "当事人编号不属于当前案件，请刷新后重新选择")
        row["id"] = row["id"] or uuid4().hex
        if row["id"] in seen_ids:
            raise HTTPException(422, "当事人编号重复")
        seen_ids.add(row["id"])
        subject = (row["subject_kind"], row["credit_code"] or row["name"])
        if subject in seen_subjects:
            raise HTTPException(422, "同一主体不能在本案中重复分类，请核对主体名称与信用代码")
        seen_subjects.add(subject)
        requires_client = key[0] == "我方" and key[1] == "当事人"
        if requires_client and not row["related_client_id"]:
            raise HTTPException(422, f"{row['name']}：必须关联实际委托客户")
        if row["related_client_id"]:
            client = await _customer_or_404(row["related_client_id"], identity, db)
            if str((client.data or {}).get("customer_type") or "客户") not in {"客户", "委托客户"} or client.status in {"已回收", "已删除"}:
                raise HTTPException(422, "关联客户必须是有效 CRM 委托客户，历史当事人须先人工确认身份")
            clients[client.id] = client
            row["related_client_name"] = client.title
            if row["is_client_principal"]:
                if row["name"] != client.title.strip():
                    raise HTTPException(422, "委托人主体名称须与所关联的 CRM 客户一致")
                personal = (client.data or {}).get("organization_type") == "个人"
                if personal and row["subject_kind"] != "自然人":
                    raise HTTPException(422, "委托人主体性质与 CRM 客户不一致")
                code = str((client.data or {}).get("identity_no" if personal else "credit_code") or "").strip().upper()
                if code and row["credit_code"] != code:
                    raise HTTPException(422, "委托人证件号码与 CRM 客户不一致")
        if key[0] == "对方" and row["related_client_id"]:
            raise HTTPException(422, "对方主体不能关联为本案委托客户")
        row["case_id"] = record.id
        rows.append(row)
    own = [row for row in rows if row["party_standpoint"] == "我方" and row["party_type"] == "当事人"]
    if not own:
        raise HTTPException(422, "请至少录入一名我方当事人")
    linked_clients = {row["related_client_id"] for row in own}
    primary_id = (record.data or {}).get("customer_record_id") or (record.data or {}).get("customer_id")
    if primary_id and (not str(primary_id).isdigit() or linked_clients != {int(primary_id)}):
        raise HTTPException(422, "我方当事人须保留案件实际委托客户关联，不能通过分类改变费用归属")
    if not primary_id and record.customer and not any(clients[key].title.strip() == record.customer.strip() for key in linked_clients):
        raise HTTPException(422, "关联委托客户与案件客户不一致，请先核对案件基本信息")
    own_positions = {row["litigation_status"] for row in own}
    for row in rows:
        if row["party_standpoint"] == "对方" and row["party_type"] == "当事人" and not row["litigation_status_overridden"]:
            if len(own_positions) != 1:
                raise HTTPException(422, "我方存在多个诉讼地位，请对对方主体启用手动覆盖并明确地位")
            expected = MIRROR_POSITIONS[next(iter(own_positions))]
            if row["litigation_status"] != expected:
                raise HTTPException(422, "对方诉讼地位应与我方镜像一致，复杂案情请启用手动覆盖")
    case_type = str((record.data or {}).get("case_type") or "")
    if case_type in {"行政案件及国家赔偿", "仲裁"} and not ({"原告", "申请人"} & {row["litigation_status"] for row in rows} and {"被告", "被申请人"} & {row["litigation_status"] for row in rows}):
        raise HTTPException(422, "请录入原告/申请人与被告/被申请人")
    projection = {"case_parties": rows, "case_party_schema_version": 1}
    for field, positions in (("plaintiffs", {"原告", "申请人"}), ("defendants", {"被告", "被申请人"}), ("third_parties", {"第三人"})):
        parties = [row for row in rows if row["party_type"] != "关联方" and row["litigation_status"] in positions]
        projection[field] = [row["name"] for row in parties]
        projection[{"plaintiffs": "plaintiff_identities", "defendants": "defendant_identities", "third_parties": "third_party_identities"}[field]] = [
            {"name": row["name"], "organization_type": "个人" if row["subject_kind"] == "自然人" else "公司企业" if row["subject_kind"] == "法人" else "其他", "identity_no": row["credit_code"]}
            for row in parties if row["credit_code"]
        ]
    if len(own_positions) == 1:
        own_position = next(iter(own_positions))
        if case_type == "刑事案件" and own_position in {"原告", "被告"}:
            projection["client_position"] = "被害人" if own_position == "原告" else "被告人/犯罪嫌疑人"
        elif case_type != "刑事案件" and own_position in {"原告", "申请人", "被告", "被申请人", "第三人"}:
            projection["client_position"] = "原告/申请人" if own_position in {"原告", "申请人"} else "被告/被申请人" if own_position in {"被告", "被申请人"} else "第三人"
    projection["plaintiff"] = "、".join(projection["plaintiffs"])
    projection["opponent"] = "、".join(projection["defendants"])
    projection["defendant"] = projection["opponent"]
    projection["our_party_names"] = [row["name"] for row in rows if row["party_standpoint"] == "我方"]
    projection["opponent_party_names"] = [row["name"] for row in rows if row["party_standpoint"] == "对方" and row["party_type"] == "当事人"]
    return projection


async def persist_classified_litigants(record, body, identity: dict, db, *, advance_creation: bool, action: str):
    from app.core.conflict_review import assess_conflict_review
    from app.core.documents import _clean_case_litigant_agents
    from app.core.legacy_sync import _sync_legacy_projection
    from app.core.system import _record_dict
    from app.models import WorkflowEvent

    projection = await prepare_case_parties(record, body.case_parties, identity, db)
    previous = dict(record.data or {})
    if previous.get("case_party_schema_version") != 1:
        previous["party_classification_legacy_source"] = {key: previous.get(key) for key in ("plaintiffs", "defendants", "third_parties", "plaintiff", "opponent", "plaintiff_identities", "defendant_identities", "third_party_identities", "unclassified_case_parties")}
    data = {**previous, **projection, "party_classification_status": "已分类"}
    for field in ("plaintiff_agents", "defendant_agents", "third_party_agents"):
        data[field] = _clean_case_litigant_agents(getattr(body, field))
    if advance_creation and str(previous.get("case_creation_step") or "") in {"basic", "litigants"}:
        data["case_creation_step"] = "litigants"
    record.data = data
    await assess_conflict_review(record, identity, db, trigger="case_save")
    db.add(WorkflowEvent(record_id=record.id, action=action, from_status=record.status, to_status=record.status, operator=identity["username"], comment=body.comment))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return _record_dict(record)
