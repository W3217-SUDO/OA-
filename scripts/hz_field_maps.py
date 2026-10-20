"""旧字段与新版页面数据契约的显式对应关系。"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal


CUSTOMER = {
    "customer_guid": "CustomerGuid", "short_name": "CustomerShortName",
    "phone": "ContactPhone", "fax": "Fax", "postal_code": "Zip",
    "province": "Province", "city": "City", "industry": "Industry",
    "output_value": "ProductionValue", "legacy_customer_type_name": "CustomerTypeName",
    "cooperation_status": "CooperatioSituation", "customer_source": "CustomerSourceType",
    "website": "WebSite", "organization_nature": "CompanyTypeName",
    "gb_classification": "GBTypeName", "registered_capital": "RegisteredCapital",
    "registration_year": "RegistrationDate", "registration_region": "RegistrationCity",
    "registration_postal_code": "RegistrationZip", "registered_address": "RegistrationAddress",
    "contact_address": "ContactAddress", "organization_code": "OrganizationCode",
    "credit_code": "LicenseNo", "bank_name": "AccountBankName", "bank_account": "BankAccount",
    "file_date": "InputDate", "last_contact_at": "LastContactTime", "level": "CustomerLevelName",
    "legal_representative": "LegalAgentName", "legal_agent_id_no": "LegalAgentIdNo",
    "legal_agent_title": "LegalAgentTitle", "prepaid_amount": "PrePaidAmount",
    "invoice_title": "CustomerName", "taxpayer_id": "LicenseNo",
    "invoice_phone": "ContactPhone", "invoice_address": "RegistrationAddress",
}
CONTRACT = {
    "contract_guid": "ContractGuid", "ref_contract_no": "RefContractNo",
    "external_contract_no": "RefContractNo", "contract_type_id": "ContractType",
    "charging_type_id": "ChargingType", "amount": "ContractMoney", "contract_money": "ContractMoney",
    "tax_rate": "TaxRate", "contract_begin_date": "ContractBeginDate",
    "contract_end_date": "ContractEndDate", "signed_at": "ContractBeginDate",
    "start_date": "ContractBeginDate", "end_date": "ContractEndDate",
    "approval_count": "AuditRoundId", "approved_at": "AuditDate", "remark": "Remark",
    "business_owner": "BusinessOwner",
    "source_person": "BusinessOwner",
}
CASE = {
    "cause_or_charge": "CauseName", "right_type_id": "CaseRightTypeId",
    "source_person": "CaseOriginPeople", "business_owner": "BusinessOwner",
    "assistant_username": "CaseAssistant", "assistant": "CaseAssistantName",
    "investigator_username": "Investigator", "investigator": "InvestigatorName",
    "plaintiff": "AppellantNames", "defendant": "AppelleeNames", "opponent": "AppelleeNames",
    "court": "FirstIntanceCourt", "court_case_no": "FirstIntanceCaseNo",
    "judge": "FirstIntanceJudge", "clerk": "FirstIntanceClerk", "courtroom": "FirstIntanceCourtRoom",
    "filing_date": "FirstIntanceRegisterDate", "judgment_date": "FirstIntanceJudgmentDate",
    "notarial_no": "NotarialNos", "warehouse": "DepositAddress", "deposit_address": "DepositAddress",
    "counsel_start": "ConsultantBeginDate", "counsel_end": "ConsultantEndDate",
    "archive_no": "ArchivedFileNo", "case_closed_at": "ClosingTime", "archive_submitted_at": "ToAuditTime",
    "archive_submitter": "ToAuditApplicant", "archive_submit_comment": "ToAuditRemark",
    "archive_internal_reviewer": "InternalAuditor", "archive_internal_reviewed_at": "InternalAuditedTime",
    "archive_internal_review_comment": "InternalAuditedRemark", "archive_reviewer": "Auditor",
    "archive_reviewed_at": "AuditedTime", "archived_at": "AuditedTime",
    "archive_review_comment": "AuditedRemark", "execution_status_code": "ExecutionStatus",
    "cause_of_action": "CauseName", "case_register_date": "CaseRegisterDate",
    "hearing_lawyer": "CourtLawyer", "hearing_lawyer_username": "CourtLawyer",
    "hearing_lawyer_name": "CourtLawyerName", "litigation_subject": "LitigationAmount",
    "judgment_amount": "SettlementAmount", "case_divisional_date": "CaseDivisionalDate",
    "notary_no": "NotarialNos", "original_case_no": "OriginalCaseNo",
    "public_security_name": "PublicSecurityUnitName", "first_procuratorate_name": "FirstIntanceProcuratorateUnitName",
    "second_procuratorate_name": "SecondIntanceProcuratorateUnitName", "last_procuratorate_name": "LastIntanceProcuratorateUnitName",
}
for prefix, source in (("first_instance", "FirstIntance"), ("second_instance", "SecondIntance"),
    ("last_instance", "LastIntance"), ("execution_instance", "ExecutionIntance")):
    for key, column in (("court", "Court"), ("judge", "Judge"), ("clerk", "Clerk"),
        ("case_no", "CaseNo"), ("register_date", "RegisterDate"), ("lawful_day", "LawfulDay"),
        ("judgment_date", "JudgmentDate"), ("courtroom", "CourtRoom")):
        CASE[f"{prefix}_{key}"] = source + column
for prefix, source in (("first_court", "FirstIntance"), ("second_court", "SecondIntance"),
    ("last_court", "LastIntance"), ("execution_court", "ExecutionIntance")):
    for key, column in (("name", "Court"), ("case_no", "CaseNo"), ("courtroom", "CourtRoom"),
        ("filing_date", "RegisterDate"), ("hearing_date", "LawfulDay"), ("judgment_date", "JudgmentDate")):
        CASE[f"{prefix}_{key}"] = source + column
INVESTIGATION = {
    "source_owner": "Indicter", "publisher": "CreateUser", "auditor": "Auditor",
    "authorized_from": "AuthorizationBeginTime", "authorized_to": "AuthorizationEndTime",
    "province": "Province", "city": "City", "case_type_id": "CaseTypeId",
    "assigner": "CreateUser",
}
TASK = {
    "assistant": "Assistant", "publisher": "CreateUser", "source_owner": "CreateUser",
    "start_date": "BeginTime", "end_date": "EndTime", "deadline": "EndTime",
    "authorized_from": "BeginTime", "authorized_to": "EndTime",
    "province": "Province", "city": "City", "district": "District",
    "assigner": "CreateUser", "started_at": "BeginTime", "ended_at": "EndTime",
}
CLUE = {
    "platform": "PlatformName", "store_name": "StoreName", "store_url": "StoreUrl",
    "address": "Address", "location_address": "LocationAddress", "source_url": "StoreUrl",
    "opponent": "Indictee", "indictee": "Indictee", "submitted_at": "ToAuditTime",
    "reviewer": "Auditor", "reviewed_at": "AuditTime", "review_comment": "AuditRemark",
    "rejection_reason": "AuditRemark", "merge_into_case_no": "AuditNeedMergeCaseNo",
    "converted_case_no": "CaseNo", "customer_reviewer": "CustomerAuditor",
    "customer_reviewed_at": "CustomerAuditTime", "customer_review_comment": "CustomerAuditRemark",
    "investigation_task_no": "InvestigationTaskNo",
    "shop_name": "StoreName", "shop_id": "StoreId", "has_product": "HasProduct",
    "investigated_at": "InvestigationDate", "investigator_remark": "Remark",
}
EVIDENCE = {
    "notary_office": "NotaryOrganization", "notary_no": "NotarialNo", "notarial_no": "NotarialNo",
    "notary_date": "NotarialObtainDate", "evidence_address": "EvidenceAddress",
    "deposit_address": "DepositAddress", "invoice_no": "InvoiceNo", "storage_location": "StorageLocationName",
    "storage_location_no": "StorageLocationNo", "warehouse_no": "WarehouseNo", "amount": "Amount",
    "collected_at": "EvidenceDate", "notary_institution": "NotaryOrganization",
    "certificate_no": "NotarialNo", "certificate_issued_date": "NotarialObtainDate",
    "warehouse": "DepositAddress", "notarization_no": "NotarialNo",
}
IPR = {
    "application_no": "CaseRequestNo", "application_date": "CaseRequestDate",
    "applicant": "ApplicantName", "case_inventor": "CaseInventor", "inventor": "CaseInventor",
    "case_manager": "CaseOfficer", "case_manager_username": "CaseOfficer",
    "case_source": "CaseOriginPeople", "case_source_username": "CaseOriginPeople",
    "source_date": "CaseOriginDate", "agent": "Procurator", "agent_username": "Procurator",
    "writer": "Copywriter", "writer_username": "Copywriter", "submitter": "CaseSubmitter",
    "submitter_username": "CaseSubmitter", "submit_date": "CaseSubmitDate",
    "case_submit_date": "CaseSubmitDate", "accepted_at": "CaseRegisterDate",
    "acceptance_date": "CaseRegisterDate", "authorization_date": "AuthorizationDate",
    "deadline": "Deadline", "annual_fee_year": "FirstAnnualYear", "rate": "CostSlowRate",
}
OFFICIAL = {
    "is_electronic_seal": "IsElectronicSeal", "is_offline_print": "IsOfflinePrint",
    "print_quantity": "PrintQuantity", "application_date": "ApplicationDate",
    "official_document_begin_date": "OfficialDocumentBeginDate",
    "official_document_end_date": "OfficialDocumentEndDate", "reviewer": "Auditor",
    "reviewed_at": "AuditTime", "review_comment": "AuditRemark", "printed_at": "PrintTime",
    "printed_by": "Printer", "approval_count": "AuditRoundId", "seal_type_id": "SealType",
}
MAPS = {"customer": CUSTOMER, "contract": CONTRACT, "case": CASE,
    "investigation": INVESTIGATION, "task": TASK, "clue": CLUE, "evidence": EVIDENCE,
    "ipr_case": IPR, "official_outgoing": OFFICIAL}


def text(value):
    return "" if value is None else str(value).strip()


def json_value(value):
    if isinstance(value, dict):
        return {k: json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return {"hex": value.hex()}
    return value


def snake(value):
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()


def enabled(value):
    return text(value).upper() in {"Y", "T", "TRUE", "1", "YES"}


def split_people(value):
    return [v.strip() for v in re.split(r"[,，;；、|]", text(value)) if v.strip()]


def mapped_data(module, row):
    data = {snake(k): json_value(v) for k, v in row.items()}
    for key, column in MAPS.get(module, {}).items():
        if column in row:
            data[key] = json_value(row[column])
    for key, column in {"created_by": "CreateUser", "updated_by": "ChangeUser"}.items():
        data[key] = text(row.get(column))
    if module == "customer":
        for key, column in {"is_assisted": "IsAssisted", "is_shared": "IsShared", "fee_reduction": "IsFeeReducing"}.items():
            data[key] = "是" if enabled(row.get(column)) else "否"
        data["is_vip"] = text(row.get("CustomerLevelName")).upper() == "VIP"
    if module == "contract":
        data["is_changed"] = enabled(row.get("IsChanged"))
    if module == "case":
        for key, column in {"handling_lawyer_usernames": "CaseLawyer", "handling_lawyers": "CaseLawyerName",
            "plaintiffs": "AppellantNames", "plaintiff_agents": "AppellantAgent", "defendants": "AppelleeNames",
            "defendant_agents": "AppelleeAgent", "third_parties": "TheThirdNames", "third_party_agents": "TheThirdAgent",
            "notary_nos": "NotarialNos", "assistant_usernames": "CaseAssistant"}.items():
            data[key] = split_people(row.get(column))
        data["archive_type"] = {1: "normal", 2: "deficit"}.get(row.get("ArchiveTypeId"), "")
    if module in {"investigation", "task"}:
        data["authorization_scope"] = "全国" if text(row.get("InvestigationScope")) in {"N", "10", "全国"} else "区域"
        data["customer_review"] = enabled(row.get("NeedToAuditOnCustomer"))
    if module == "clue":
        for key in ("province", "city", "district"):
            display = row.get(key.title() + "Zh")
            if text(display):
                data[key] = text(display)
        for key, column in {"has_product": "HasProduct", "has_tort": "HasTort", "audit_need_merge_case": "AuditNeedMergeCase"}.items():
            data[key] = enabled(row.get(column))
    return data
