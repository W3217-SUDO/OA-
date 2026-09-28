"""执行可核实的利冲检索，并显式保留现有资料无法判断的规则。"""

from app.areas.crm.conflict_rule_catalog import get_conflict_rule_catalog
from app.core.conflict_review_facts import current_counsel, fingerprint, normalized_name, party_matches


KINDS = {"BLOCK": "absolute", "WAIVER_REQUIRED": "relative", "SPECIAL": "special"}
CRIMINAL_RULES = {"R-B03", "R-B04", "R-D02", "R-E03"}


def evaluate_conflict_facts(facts: dict) -> dict:
    catalog = get_conflict_rule_catalog()
    subjects = [item for item in facts["subjects"] if item["module"] != "seal"]
    if not subjects:
        subjects = facts["subjects"]
    findings = {}
    matched_people = {}
    matched_matters = {}
    for subject in subjects:
        subjects.extend(subject.get("merged_sources") or [])
    team_tokens = {token for subject in subjects for token in subject["lawyers"]}
    team_people = {person["id"]: person for person in facts["people"] if person["username"] in team_tokens or person["name"] in team_tokens}

    def add(rule_id: str, reason: str, evidence: str) -> None:
        item = findings.setdefault(rule_id, {"reasons": [], "evidence": []})
        if reason not in item["reasons"]:
            item["reasons"].append(reason)
        if evidence not in item["evidence"]:
            item["evidence"].append(evidence)

    for subject in subjects:
        lawyers = set(subject["lawyers"])
        for person in facts["people"]:
            matched = [party for party in subject["opponents"] if party_matches(party, person["name"], person["identity"])]
            if not matched:
                continue
            own_lawyer = person["username"] in lawyers or person["name"] in lawyers
            matched_people[person["id"]] = person
            add("R-A01" if own_lawyer else "R-B02", "案件对方与承办律师或本所人员身份资料匹配，须核实主体及代理关系", f"本案对方：{'、'.join(item['name'] for item in matched)}；本所人员：{person['name']}")
        if facts["company_name"] and any(normalized_name(party["name"]) == normalized_name(facts["company_name"]) for party in subject["opponents"]):
            add("R-B02", "本案对方名称与本公司配置名称相同，须核实登记主体", facts["company_name"])
        for other in facts["matters"]:
            if other["module"] not in {"case", "ipr_case"}:
                continue
            same_lawyer = bool(lawyers & set(other["lawyers"]))
            same_case = bool(set(subject["court_numbers"]) & set(other["court_numbers"])) or bool(subject["copy_root"] and subject["copy_root"] == other["copy_root"])
            reversed_side = any(party_matches(party, client["name"], client["identity"]) for party in subject["opponents"] for client in other["clients"]) or any(party_matches(party, client["name"], client["identity"]) for party in other["opponents"] for client in subject["clients"])
            evidence = f"关联案件 {other['number']}；委托人 {other['customer']}；经办律师 {'、'.join(other['lawyers']) or '未完整登记'}"
            if reversed_side and same_case:
                matched_matters[other["id"]] = other
                add("R-D01" if same_lawyer else "R-E01", "法院案号或复制来源相同，且现有记录显示对立委托关系，须核实同案及有效委托", evidence)
                if other.get("ended"):
                    add("R-D04" if same_lawyer else "R-E02", "同案历史委托已结束且双方关系倒置，须核实后续程序", evidence)
            if reversed_side and not other.get("ended"):
                matched_matters[other["id"]] = other
                add("R-D06" if same_lawyer else "R-E05", "现有在办记录存在委托人与对方交叉关系，须核实委托是否在同一时段存续", evidence)
                if same_lawyer and (current_counsel(other) or current_counsel(subject)):
                    add("R-D03", "法律顾问服务期间出现同一律师的对立委托关系，包含新顾问委托反向核查", evidence)
            if same_case and "刑事" in subject["case_type"] and "刑事" in other["case_type"] and normalized_name(subject["customer"]) != normalized_name(other["customer"]):
                if subject["client_position"] in {"犯罪嫌疑人", "被告人", "被告", "被告人/犯罪嫌疑人"} and other["client_position"] in {"犯罪嫌疑人", "被告人", "被告", "被告人/犯罪嫌疑人"}:
                    matched_matters[other["id"]] = other
                    add("R-D02" if same_lawyer else "R-E03", "同一刑事案号出现不同辩方委托，须核实同案认定与在先同意", evidence)

    result = []
    known_types = {item["case_type"] for item in subjects if item["case_type"]}
    known_noncriminal = bool(known_types) and all(item in {"民事案件", "民事争议", "仲裁", "行政案件及国家赔偿", "法律顾问", "知识产权诉讼", "知识产权非诉", "知识产权案件"} for item in known_types)
    for rule in catalog["rules"]:
        if rule["id"] in CRIMINAL_RULES and known_noncriminal:
            continue
        matched = findings.get(rule["id"])
        result.append({
            "rule_id": rule["id"], "title": rule["title"], "kind": KINDS[rule["outcome_if_confirmed"]],
            "reason": "；".join(matched["reasons"]) if matched else "现有资料不足以自动排除本条情形，请结合所需事实核实",
            "evidence": matched["evidence"] if matched else [],
            "unresolved": not bool(matched), "required_facts": list(rule["required_facts"]),
            "manual_boundary": rule["manual_boundary"], "status": "pending", "feedback": None, "decision": None,
            **({"branches": rule["branches"]} if "branches" in rule else {}),
        })
    # 只纳入相关匹配和事实快照。无关历史记录增加不能撤销已完成的审查。
    signature = {
        "rules_version": catalog["version"], "subjects": facts["subjects"],
        "people": [value for _, value in sorted({**team_people, **matched_people}.items())], "company_name": facts["company_name"],
        "matched_matters": [value for _, value in sorted(matched_matters.items())],
        "matches": {key: value for key, value in sorted(findings.items())},
        "rules": [{"id": item["id"], "outcome": item["outcome_if_confirmed"], "facts": item["required_facts"]} for item in catalog["rules"]],
    }
    return {"fingerprint": fingerprint(signature), "facts_snapshot": signature, "rule_catalog_version": catalog["version"], "findings": result,
            "missing_facts": sorted({fact for item in result if item["unresolved"] for fact in item["required_facts"]})}
