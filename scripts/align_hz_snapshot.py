"""沪知快照导入后的页面字段对齐：员工账号、负责人、客户经理、状态、法院名称。

在 import_hz_snapshot.py --apply 之后运行；旧表（HR_Staff、BAS_Court、BAS_Case_Phase、
CRM_Customer_Coordinator 等）须已在目标库中。只处理 data.migration_source 为 hz_crm_20260930 的记录，
且只替换占位值（负责人 admin、状态“历史数据”、法院编号），页面上后来改过的值不覆盖。
员工账号使用随机密码，不沿用旧系统密码，须由管理员重置后才能登录。
"""
import json, os, secrets, sys
from collections import Counter
from pathlib import Path

for candidate in (Path(__file__).resolve().parents[1] / "apps" / "api-server", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break
import psycopg
from psycopg.types.json import Jsonb
from app.security import hash_password
from app.core.constants import CONTRACT_APPROVED_STATUS

SOURCE = "hz_crm_20260930"
CONTRACT = {0: "草稿", 10: "审批中", 20: CONTRACT_APPROVED_STATUS, 30: "已拒绝", 40: "已回收", 60: "已归档", 80: "已完成"}
INV = {0: "待分配", 10: "进行中", 20: "已完成", 30: "已取消"}
TASK = {0: "待接收", 10: "处理中", 15: "待确认", 20: "已完成", 30: "已拒绝", 40: "已取消"}
CLUE = {0: "草稿", 10: "待审批", 15: "待客户审核", 20: "待取证", 30: "已取证", 35: "待公证", 40: "已转案件", 50: "已驳回"}
COURT_KEYS = {"court": "court_code", "first_instance_court": "first_instance_court_code", "second_instance_court": "second_instance_court_code",
              "last_instance_court": "last_instance_court_code", "execution_instance_court": "execution_instance_court_code",
              "first_court_name": "first_court_code", "second_court_name": "second_court_code",
              "last_court_name": "last_court_code", "execution_court_name": "execution_court_code"}


def s(v):
    return "" if v is None else str(v).strip()


def inactive(v):
    return s(v).upper() in {"N", "F", "0"}


dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
report = Counter()
with psycopg.connect(dsn) as pg:
    def rows(sql, params=()):
        c = pg.execute(sql, params); f = [x.name for x in c.description]; return [dict(zip(f, r)) for r in c.fetchall()]

    # 1. 员工账号：让用户名能显示成姓名；密码为随机值，不沿用旧密码
    departments = {r["DepartmentId"]: s(r["DepartmentName"]) for r in rows('select "DepartmentId","DepartmentName" from "HR_Department"')}
    existing = {r["username"] for r in rows("select username from users")}
    for st in rows('select * from "HR_Staff" order by "StaffId"'):
        username = s(st["StaffName"]).lower()
        if not username or username in existing or not s(st.get("StaffChName")):
            report["staff_skipped"] += 1
            continue
        pg.execute(
            """insert into users (username, display_name, department, password_hash, role, role_ids, profile, is_active,
                                  failed_login_attempts, must_change_password, created_at)
               values (%s, %s, %s, %s, 'user', %s, %s, %s, 0, true, now())""",
            (username, s(st["StaffChName"])[:64], departments.get(st.get("DepartmentId"), "")[:64] or "沪知", hash_password(secrets.token_urlsafe(32)),
             Jsonb(["user"]), Jsonb({"migration_source": SOURCE, "legacy_staff_no": s(st.get("StaffNo")), "legacy_department_id": s(st.get("DepartmentId"))}),
             not inactive(st.get("IsActived"))),
        )
        existing.add(username); report["staff_created"] += 1
    users = existing

    # 2. 字典
    courts = {s(r["CourtCode"]): s(r["CourtName"]) for r in rows('select "CourtCode","CourtName" from "BAS_Court"') if s(r["CourtCode"])}
    phases = {r["CasePhaseId"]: s(r["CasePhaseName"]) for r in rows('select "CasePhaseId","CasePhaseName" from "BAS_Case_Phase"')}
    coordinators = {}
    for r in rows('select "CustomerNo","StaffName" from "CRM_Customer_Coordinator" order by "CoordinatorId"'):
        coordinators.setdefault(s(r["CustomerNo"]), []).append(s(r["StaffName"]).lower())

    def owner_of(value):
        name = s(value).lower()
        return name if name in users else None

    plans = {
        "customer": ('select * from "CRM_Customer"', "CustomerNo", lambda r: r.get("BusinessOwner")),
        "contract": ('select * from "FCM_Contract"', "ContractNo", lambda r: r.get("BusinessOwner")),
        "case": ('select * from "Legal_Case"', "CaseNo", lambda r: r.get("BusinessOwner")),
        "investigation": ('select * from "Legal_Investigation"', "InvestigationNo", lambda r: r.get("BusinessOwner")),
        "task": ('select * from "Legal_Investigation_Task"', "TaskNo", lambda r: r.get("Investigator") or r.get("CreateUser")),
        "clue": ('select * from "Legal_Investigation_Clue"', "ClueNo", lambda r: r.get("Investigators") or r.get("CreateUser")),
        "ipr_case": ('select * from "IPR_Case"', "CaseNo", lambda r: r.get("CaseOfficer")),
    }
    for module, (sql, key, owner_fn) in plans.items():
        current = {r["serial_no"]: r for r in rows(
            "select id, serial_no, owner, status, data from business_records where module=%s and data->>'migration_source'=%s", (module, SOURCE))}
        for src in rows(sql):
            rec = current.get(s(src[key]))
            if not rec:
                continue
            data = dict(rec["data"] or {}); owner = rec["owner"]; status = rec["status"]; changed = False
            wanted_owner = owner_of(owner_fn(src))
            if owner == "admin" and wanted_owner and wanted_owner != "admin":
                owner = wanted_owner; changed = True; report[f"{module}_owner"] += 1
            if module == "customer":
                managers = [m for m in dict.fromkeys([s(src.get("BusinessOwner")).lower(), *coordinators.get(s(src[key]), [])]) if m in users]
                if managers and not data.get("customer_managers"):
                    data["customer_managers"] = managers; changed = True; report["customer_managers"] += 1
            if status == "历史数据":
                new = None
                if module == "contract":
                    new = CONTRACT.get(src.get("ContractStatus") if src.get("ContractStatus") is not None else 0)
                    if inactive(src.get("IsActived")): new = "已回收"
                elif module == "case":
                    arch = src.get("ArchiveStatus")
                    new = "已归档" if arch == 20 else "待归档审核" if arch == 10 else "亏损内审" if arch == 7 else phases.get(src.get("CasePhaseId"))
                    if inactive(src.get("IsActived")): new = "已删除"
                    data["case_phase"] = phases.get(src.get("CasePhaseId"), "")
                elif module == "investigation":
                    new = INV.get(src.get("Status")); new = "已取消" if inactive(src.get("IsActived")) else new
                elif module == "task":
                    new = TASK.get(src.get("TaskStatus")); new = "已取消" if inactive(src.get("IsActived")) else new
                elif module == "clue":
                    new = CLUE.get(src.get("Status")); new = "已删除" if inactive(src.get("IsActived")) else new
                if new and new != status:
                    status = new; changed = True; report[f"{module}_status"] += 1
            if module == "case":
                for name_key, code_key in COURT_KEYS.items():
                    value = s(data.get(name_key))
                    if value in courts:
                        data[code_key] = value; data[name_key] = courts[value]; changed = True; report["case_court_name"] += 1
            if changed:
                pg.execute("update business_records set owner=%s, status=%s, data=%s where id=%s", (owner, status, Jsonb(data), rec["id"]))
    pg.commit()
print(json.dumps(dict(report), ensure_ascii=False, sort_keys=True))
