"""本地 API 端到端冒烟验收。

默认连接 http://localhost:8000，创建的测试数据使用 SMOKE 前缀并在结束时清理。
可通过 API_BASE_URL、SMOKE_USERNAME、SMOKE_PASSWORD 覆盖连接参数。
"""

from __future__ import annotations

import json
import io
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta


BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE}/api/v1"
USERNAME = os.getenv("SMOKE_USERNAME", "admin")
PASSWORD = os.getenv("SMOKE_PASSWORD", "")
TOKEN = ""
PASSED: list[str] = []


def call(method: str, path: str, body=None, *, expected=(200,), raw=False, headers=None):
    url = path if path.startswith("http") else f"{API}{path}"
    request_headers = dict(headers or {})
    if TOKEN:
        request_headers["Authorization"] = f"Bearer {TOKEN}"
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
            status = response.status
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        status = exc.code
        content_type = exc.headers.get("Content-Type", "")
    if status not in expected:
        detail = payload.decode("utf-8", errors="replace")
        raise AssertionError(f"{method} {path}: expected {expected}, got {status}: {detail}")
    if raw:
        return status, payload, content_type
    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))


def login(username: str, password: str, *, expected=(200,)):
    data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    request = urllib.request.Request(
        f"{API}/auth/login",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status, payload = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, payload = exc.code, exc.read()
    if status not in expected:
        raise AssertionError(f"login expected {expected}, got {status}: {payload!r}")
    return json.loads(payload.decode()) if payload else None


def multipart_upload(path: str, fields: dict[str, object], filename: str, content: bytes, *, expected=(201,)):
    boundary = f"----SunholdSmoke{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: text/plain\r\n\r\n",
            content,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    request = urllib.request.Request(
        f"{API}{path}",
        data=b"".join(chunks),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status_code = response.status
            payload = response.read()
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        payload = exc.read()
    if status_code not in expected:
        raise AssertionError(f"upload expected {expected}, got {status_code}: {payload!r}")
    return json.loads(payload.decode("utf-8")) if payload else None


def set_task_test_data(task_id: int, updates: dict[str, object]):
    """仅在本地冒烟数据库中回拨任务日期，不向生产 API 增加测试后门。"""
    payload = json.dumps(updates, ensure_ascii=False).replace("'", "''")
    sql = f"UPDATE business_records SET data = (COALESCE(data, '{{}}'::json)::jsonb || '{payload}'::jsonb) WHERE id = {int(task_id)} AND module = 'task';"
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "sh", "-c", 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        input=sql, text=True, capture_output=True, timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"设置任务测试日期失败：{result.stderr.strip()}")


def set_customer_test_updated_at(customer_id: int, timestamp: str):
    """仅在本地冒烟库中构造相同绝对时间，验证稳定排序与时区处理。"""
    escaped_timestamp = timestamp.replace("'", "''")
    sql = (
        "UPDATE business_records "
        f"SET updated_at = '{escaped_timestamp}'::timestamptz "
        f"WHERE id = {int(customer_id)} AND module = 'customer';"
    )
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "sh", "-c", 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        input=sql, text=True, capture_output=True, timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"设置客户最近更新时间失败：{result.stderr.strip()}")


def clear_customer_test_modifier(customer_id: int):
    """模拟迁移前无 modifier 标记的历史客户，验证流程事件回退。"""
    sql = (
        "UPDATE business_records "
        "SET data = COALESCE(data, '{}'::json)::jsonb - 'last_modified_by' "
        f"WHERE id = {int(customer_id)} AND module = 'customer';"
    )
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "sh", "-c", 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        input=sql, text=True, capture_output=True, timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"清除客户修改人测试标记失败：{result.stderr.strip()}")


def local_db_scalar(sql: str, *, label: str) -> int:
    """Run a read-only scalar assertion against the local smoke PostgreSQL."""
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "sh", "-c", 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'],
        input=sql, text=True, capture_output=True, timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"{label}查询失败：{result.stderr.strip()}")
    value = result.stdout.strip().splitlines()
    if len(value) != 1 or not value[0].isdigit():
        raise AssertionError(f"{label}返回值无效：{result.stdout.strip()!r}")
    return int(value[0])


def passed(name: str):
    PASSED.append(name)
    print(f"[PASS] {name}")


def contract_approve_as(username: str, contract_id: int, approved: bool, comment: str, *, expected=(200,)):
    """Exercise the contract node with the assigned approver instead of an administrator override."""
    global TOKEN
    previous = TOKEN
    TOKEN = login(username, "SmokePass2026!")["access_token"]
    try:
        return call("POST", f"/contracts/{contract_id}/approve", {"approved": approved, "comment": comment}, expected=expected)
    finally:
        TOKEN = previous


def main():
    global TOKEN
    if not PASSWORD:
        raise RuntimeError("SMOKE_PASSWORD 未配置；请在本机 .env 中设置测试账号密码")
    suffix = f"{int(time.time())}{uuid.uuid4().hex[:5]}"
    serial = lambda prefix: f"SMOKE-{prefix}-{suffix}"
    records: list[int] = []
    users: list[int] = []
    templates: list[int] = []
    agents: list[int] = []
    attachments: list[int] = []
    hearings: list[int] = []
    receivables: list[int] = []
    incoming_payments: list[int] = []
    transactions: list[int] = []
    reconciliations: list[int] = []
    payment_packages: list[int] = []
    settlement_applications: list[int] = []
    system_parameters: list[int] = []
    system_menus: list[int] = []
    departments: list[int] = []
    job_roles: list[int] = []
    communications: list[int] = []
    security_policy_original = None
    system_menu_original = None
    system_configs_original: dict[str, dict] = {}

    def create_record(module: str, status: str, title: str, data=None, *, department="上海分所", owner=USERNAME):
        path = "/customers" if module == "customer" else ("/contracts" if module == "contract" else "/records")
        effective_status = "潜在" if module == "customer" else status
        payload = {
            "serial_no": f"{serial(module.upper())}-{uuid.uuid4().hex[:4]}",
            "title": title,
            "status": effective_status,
            "owner": owner,
            "department": department,
            "description": "自动验收数据",
            "data": data or {},
        }
        if module != "customer":
            payload.update({"module": module, "customer": "冒烟测试客户"})
        item = call(
            "POST",
            path,
            payload,
            expected=(201,),
        )
        if module == "customer" and status == "公海":
            item = call("POST", f"/customers/{item['id']}/release", {"comment": "构造公海客户测试数据"})
        records.append(item["id"])
        return item

    try:
        call("GET", f"{BASE}/health", expected=(200,))
        login(USERNAME, "wrong-password", expected=(401,))
        TOKEN = login(USERNAME, PASSWORD)["access_token"]
        admin_token = TOKEN
        # 清理因上一次进程中断而留下的、带明确 SMOKE 标识的本地测试记录。
        # 生产环境不存在 testing cleanup 路由，普通业务数据也不会命中此条件。
        for smoke_module in ["customer", "contract", "case", "task", "finance", "finance_settlement", "document", "seal", "report", "hr", "warehouse", "investigation", "clue", "notary", "evidence"]:
            stale = call("GET", f"/records?module={smoke_module}&keyword=SMOKE&page_size=100")["items"]
            for stale_item in stale:
                # 搜索会命中关联字段中的 SMOKE；清理接口仍应拒绝没有明确测试标识的记录。
                call("DELETE", f"/testing/records/{stale_item['id']}", expected=(204, 403, 404))
        # A killed smoke process can leave its generated accounts behind even
        # after record cleanup.  Remove only the explicit smoke namespace
        # before creating users with fixed display-name test fixtures.
        for stale_user in call("GET", "/system/users?keyword=smoke")["items"]:
            if str(stale_user.get("username") or "").lower().startswith(("smoke_", "xsmoke_")):
                call("DELETE", f"/system/users/{stale_user['id']}", expected=(204, 404))
        profile = call("GET", "/auth/me")
        assert profile["username"] == USERNAME and profile["is_active"] is True
        assert all(key in profile for key in ["email", "office_phone", "mobile", "menu_auto_collapse"])
        directory = call("GET", "/users/directory")["items"]
        assert directory and all(item["is_active"] is True for item in directory)
        unchanged_profile = call("PATCH", "/auth/me", {})
        assert unchanged_profile["username"] == USERNAME
        saved_profile = call("PATCH", "/auth/me", {key: profile[key] for key in ["email", "office_phone", "mobile", "menu_auto_collapse"]})
        assert saved_profile["menu_auto_collapse"] in {"yes", "no"}
        dashboard = call("GET", "/dashboard")
        assert dashboard["source"] == "realtime" and len(dashboard["metrics"]) == 8
        assert len(dashboard["case_trend"]) == 10
        assert all(item["value"] >= 0 for item in dashboard["case_trend"])
        assert sum(item["value"] for item in dashboard["civil_distribution"]) == len(dashboard["latest_cases"]) or len(dashboard["latest_cases"]) == 15
        passed("健康检查、登录鉴权、个人资料和控制台数据")

        username = f"smoke_{suffix}".lower()
        user = call("POST", "/system/users", {"username": username, "display_name": "冒烟用户", "password": "SmokePass2026!", "role": "user", "profile": {"employee_no": f"E-{suffix}", "mobile": "13800000000"}}, expected=(201,))
        assert user["profile"]["employee_no"] == f"E-{suffix}" and user["mobile"] == "13800000000"
        users.append(user["id"])
        forced_name = f"smoke_first_login_{suffix}".lower()
        forced_user = call("POST", "/system/users", {"username": forced_name, "display_name": "首次改密用户", "password": "SmokePass2026!", "role": "user", "must_change_password": True}, expected=(201,))
        users.append(forced_user["id"])
        assert forced_user["must_change_password"] is True
        forced_login = login(forced_name, "SmokePass2026!")
        assert forced_login["must_change_password"] is True and forced_login["user"]["must_change_password"] is True
        TOKEN = forced_login["access_token"]
        call("GET", "/dashboard", expected=(428,))
        assert call("GET", "/auth/me")["must_change_password"] is True
        changed_first_login = call("PATCH", "/auth/me", {"current_password": "SmokePass2026!", "new_password": "ChangedPass2026!"})
        assert changed_first_login["must_change_password"] is False
        assert call("GET", "/dashboard")["source"] == "realtime"
        TOKEN = admin_token
        call("DELETE", f"/system/users/{forced_user['id']}", expected=(204,)); users.remove(forced_user["id"])
        inactive_name = f"smoke_inactive_{suffix}".lower()
        inactive_user = call("POST", "/system/users", {"username": inactive_name, "display_name": "停用员工账号", "password": "SmokePass2026!", "role": "user", "is_active": False}, expected=(201,))
        users.append(inactive_user["id"])
        assert inactive_user["is_active"] is False
        login(inactive_name, "SmokePass2026!", expected=(401,))
        call("DELETE", f"/system/users/{inactive_user['id']}", expected=(204,)); users.remove(inactive_user["id"])
        security_policy_original = call("GET", "/system/security-policy")
        test_policy = {"min_password_length": max(12, security_policy_original["min_password_length"]), "max_failed_attempts": 3, "lock_minutes": 1, "token_minutes": 15}
        assert call("PATCH", "/system/security-policy", test_policy)["max_failed_attempts"] == 3
        call("PATCH", f"/system/users/{user['id']}", {"password": "Only8Ab!"}, expected=(422,))
        login(username, "wrong-password", expected=(401,))
        login(username, "wrong-password", expected=(401,))
        login(username, "wrong-password", expected=(423,))
        login(username, "SmokePass2026!", expected=(423,))
        unlocked = call("POST", f"/system/users/{user['id']}/unlock")
        assert unlocked["failed_login_attempts"] == 0 and unlocked["locked_until"] is None
        user_token = login(username, "SmokePass2026!")["access_token"]
        TOKEN = user_token
        assert call("GET", "/auth/me")["role"] == "user"
        call("POST", "/system/users", {"username": f"smoke_forbidden_{suffix}".lower(), "display_name": "普通用户不得创建审批人", "password": "SmokePass2026!", "role": "auditor"}, expected=(403,))
        TOKEN = admin_token
        updated = call("PATCH", f"/system/users/{user['id']}", {"display_name": "冒烟用户已更新", "is_active": False, "profile": {"office_phone": "021-12345678"}})
        assert updated["is_active"] is False and updated["office_phone"] == "021-12345678"
        login(username, "SmokePass2026!", expected=(401,))
        TOKEN = user_token
        call("GET", "/dashboard", expected=(401,))
        TOKEN = admin_token
        call("PATCH", f"/system/users/{user['id']}", {"is_active": True, "role": "manager"})
        TOKEN = user_token
        assert call("GET", "/auth/me")["role"] == "manager"
        TOKEN = admin_token
        call("PATCH", "/system/security-policy", {key: security_policy_original[key] for key in ["min_password_length", "max_failed_attempts", "lock_minutes", "token_minutes"]})
        security_policy_original = None
        call("DELETE", f"/system/users/{user['id']}", expected=(204,)); users.remove(user["id"])
        role_permission_payload = call("GET", "/system/role-permissions")
        role_permissions = role_permission_payload["items"]
        admin_permission = next(item for item in role_permissions if item["role"] == "admin")
        user_permission = next(item for item in role_permissions if item["role"] == "user")
        assert admin_permission["data_scope"] == "全所数据"
        assert set(admin_permission["menu_keys"]) == set(role_permission_payload["available_menu_keys"])
        assert set(admin_permission["field_keys"]) == set(role_permission_payload["available_field_keys"])
        call("PATCH", "/system/role-permissions/admin", {"data_scope": admin_permission["data_scope"], "menu_keys": ["user-center", "system"], "field_keys": admin_permission["field_keys"]}, expected=(422,))
        call("PATCH", "/system/role-permissions/admin", {"data_scope": "本部门数据", "menu_keys": admin_permission["menu_keys"], "field_keys": admin_permission["field_keys"]}, expected=(422,))
        assert "user-center" in user_permission["menu_keys"] and "system" not in user_permission["menu_keys"]
        assert "customer-conflict" in user_permission["menu_keys"]
        saved_permission = call("PATCH", "/system/role-permissions/user", {"data_scope": user_permission["data_scope"], "menu_keys": user_permission["menu_keys"], "field_keys": user_permission["field_keys"]})
        assert saved_permission["menu_keys"] == user_permission["menu_keys"]
        call("PATCH", "/system/role-permissions/user", {"data_scope": "本人及共享数据", "menu_keys": ["task"], "field_keys": user_permission["field_keys"]}, expected=(422,))
        message_title = f"冒烟站内消息-{suffix}"
        sent_message = call("POST", "/notifications/send", {"recipients": [USERNAME], "title": message_title, "content": "站内消息发送、筛选、已读及软删除验收"}, expected=(201,))["items"][0]
        call("POST", "/notifications/send", {"recipients": [f"missing-{suffix}"], "title": message_title, "content": "无效接收人"}, expected=(422,))
        encoded_title = urllib.parse.quote(message_title)
        user_notification_type = urllib.parse.quote("用户通知"); unread_status = urllib.parse.quote("未读"); read_status = urllib.parse.quote("已读")
        assert any(item["id"] == sent_message["id"] for item in call("GET", f"/notifications?sent_only=true&notification_type={user_notification_type}&keyword={encoded_title}")["items"])
        inbox_message = next(item for item in call("GET", f"/notifications?read_status={unread_status}&keyword={encoded_title}")["items"] if item["id"] == sent_message["id"])
        assert call("POST", f"/notifications/{inbox_message['id']}/read")["is_read"] is True
        assert any(item["id"] == sent_message["id"] for item in call("GET", f"/notifications?read_status={read_status}&keyword={encoded_title}")["items"])
        call("DELETE", f"/notifications/{sent_message['id']}", expected=(204,))
        assert not call("GET", f"/notifications?keyword={encoded_title}")["items"]
        manager_name = f"smoke_manager_{suffix}".lower()
        peer_manager_name = f"smoke_peer_manager_{suffix}".lower()
        department_peer_name = f"smoke_department_peer_{suffix}".lower()
        member_name = f"smoke_member_{suffix}".lower()
        outsider_name = f"smoke_outsider_{suffix}".lower()
        auditor_name = f"smoke_auditor_{suffix}".lower()
        manager = call("POST", "/system/users", {"username": manager_name, "display_name": "范围经理", "department": "北京分所", "password": "SmokePass2026!", "role": "manager", "profile": {"position": "合伙人律师", "staff_role": "合伙人律师"}}, expected=(201,)); users.append(manager["id"])
        peer_manager = call("POST", "/system/users", {"username": peer_manager_name, "display_name": "同部门旁观经理", "department": "北京分所", "password": "SmokePass2026!", "role": "manager", "profile": {"position": "合伙人律师", "staff_role": "合伙人律师"}}, expected=(201,)); users.append(peer_manager["id"])
        manager_directory = next(item for item in call("GET", "/users/directory")["items"] if item["username"] == manager_name)
        assert manager_directory["position"] == "合伙人律师" and manager_directory["can_approve_contract"] is True and "合同审批" in manager_directory["job_permissions"]
        department_peer = call("POST", "/system/users", {"username": department_peer_name, "display_name": "同部门成员", "department": "北京分所", "password": "SmokePass2026!", "role": "user"}, expected=(201,)); users.append(department_peer["id"])
        member = call("POST", "/system/users", {"username": member_name, "display_name": "范围成员", "department": "深圳分所", "password": "SmokePass2026!", "role": "user"}, expected=(201,)); users.append(member["id"])
        outsider = call("POST", "/system/users", {"username": outsider_name, "display_name": "范围外人员", "department": "上海分所", "password": "SmokePass2026!", "role": "user"}, expected=(201,)); users.append(outsider["id"])
        auditor = call("POST", "/system/users", {"username": auditor_name, "display_name": "范围审批人员", "department": "上海分所", "password": "SmokePass2026!", "role": "auditor"}, expected=(201,)); users.append(auditor["id"])
        beijing_record = create_record("customer", "跟进中", "范围北京客户", {"customer_managers": [manager_name], "agency_fee_due": 300.25, "official_fee_unreceived": -40.5}, department="北京分所", owner=manager_name)
        shanghai_record = create_record("customer", "跟进中", "范围上海客户", department="上海分所", owner=outsider_name)
        own_record = create_record("customer", "跟进中", "范围本人客户", {"bank_name": "敏感银行", "bank_account": "62220000", "legal_representative": "可见法人"}, department="深圳分所", owner=member_name)
        shared_record = create_record("customer", "跟进中", "范围共享客户", {"agency_fee_due": 901.25, "official_fee_unreceived": -131.5, "bank_account": "SHARED-PRIVATE-BANK"}, department="上海分所", owner=outsider_name)
        shared_record = call("POST", f"/customers/{shared_record['id']}/share", {"recipients": [member_name], "comment": "通过专用入口构造共享客户"})
        manager_shared_record = create_record("customer", "跟进中", "范围经理共享客户", department="上海分所", owner=outsider_name)
        manager_shared_record = call("POST", f"/customers/{manager_shared_record['id']}/share", {"recipients": [manager_name], "comment": "通过专用入口构造经理共享客户"})
        shared_release_record = create_record("customer", "跟进中", "范围共享后公海客户", department="上海分所", owner=outsider_name)
        shared_release_record = call("POST", f"/customers/{shared_release_record['id']}/share", {"recipients": [member_name], "comment": "通过专用入口构造待释放共享客户"})
        shared_release_record = call("POST", f"/customers/{shared_release_record['id']}/release", {"comment": "共享关系随进入公海撤销"})
        assert shared_release_record["data"]["shared_with"] == [] and shared_release_record["data"]["is_shared"] == "否"
        shared_recycle_record = create_record("customer", "跟进中", "范围共享后回收客户", department="上海分所", owner=outsider_name)
        shared_recycle_record = call("POST", f"/customers/{shared_recycle_record['id']}/share", {"recipients": [member_name], "comment": "通过专用入口构造待回收共享客户"})
        shared_recycle_record = call("POST", f"/customers/{shared_recycle_record['id']}/recycle", {"comment": "共享关系随进入回收站撤销"})
        assert shared_recycle_record["data"]["shared_with"] == [] and shared_recycle_record["data"]["is_shared"] == "否"
        hidden_record = create_record("customer", "跟进中", "范围隐藏客户", department="深圳分所", owner=outsider_name)
        substring_manager_name = f"x{member_name}x"
        substring_manager = call("POST", "/system/users", {"username": substring_manager_name, "display_name": "用户名子串隔离成员", "department": "上海分所", "password": "SmokePass2026!", "role": "user"}, expected=(201,)); users.append(substring_manager["id"])
        substring_record = create_record("customer", "跟进中", "范围用户名子串客户", {"customer_managers": [substring_manager_name]}, department="上海分所", owner=substring_manager_name)
        shared_substring_record = create_record("customer", "跟进中", "范围共享用户名子串客户", department="上海分所", owner=outsider_name)
        shared_substring_record = call("POST", f"/customers/{shared_substring_record['id']}/share", {"recipients": [substring_manager_name], "comment": "通过专用入口构造共享用户名子串客户"})
        department_substring_manager_name = f"x{manager_name}x"
        department_substring_manager = call("POST", "/system/users", {"username": department_substring_manager_name, "display_name": "部门用户名子串成员", "department": "北京分所", "password": "SmokePass2026!", "role": "user"}, expected=(201,)); users.append(department_substring_manager["id"])
        department_substring_record = create_record("customer", "跟进中", "范围部门用户名子串客户", {"customer_managers": [department_substring_manager_name]}, department="北京分所", owner=department_substring_manager_name)
        public_record = create_record("customer", "公海", "范围公海客户", {"customer_managers": [outsider_name], "agency_fee_due": 800.75, "official_fee_unreceived": -120.5, "bank_account": "PUBLIC-PRIVATE-BANK"}, department="上海分所", owner=outsider_name)
        beijing_public_record = create_record("customer", "公海", "范围北京公海客户", {"customer_managers": [manager_name], "bank_account": "MANAGER-PUBLIC-BANK"}, department="北京分所", owner=manager_name)
        public_substring_record = create_record("customer", "公海", "范围公海用户名子串客户", {"customer_managers": [department_substring_manager_name]}, department="北京分所", owner=department_substring_manager_name)
        public_member_record = create_record("customer", "公海", "范围本人原管理公海客户", {"customer_managers": [member_name]}, department="深圳分所", owner=member_name)
        department_recycle_record = create_record("customer", "跟进中", "范围部门回收客户", {"customer_managers": [department_peer_name], "agency_fee_due": 511.25, "official_fee_unreceived": -80.75}, department="北京分所", owner=department_peer_name)
        department_recycle_record = call("POST", f"/customers/{department_recycle_record['id']}/recycle", {"comment": "构造部门回收站本部门客户"})
        outside_department_recycle_record = create_record("customer", "跟进中", "范围外部门回收客户", {"customer_managers": [outsider_name]}, department="上海分所", owner=outsider_name)
        outside_department_recycle_record = call("POST", f"/customers/{outside_department_recycle_record['id']}/recycle", {"comment": "构造部门回收站外部门客户"})
        department_recycle_substring_record = create_record("customer", "跟进中", "范围部门回收用户名子串客户", {"customer_managers": [department_substring_manager_name], "agency_fee_due": 711.5, "official_fee_unreceived": -90.25}, department="北京分所", owner=department_substring_manager_name)
        department_recycle_substring_record = call("POST", f"/customers/{department_recycle_substring_record['id']}/recycle", {"comment": "构造部门回收站子串隔离客户"})
        company_recycle_record = create_record("customer", "跟进中", "范围公司回收站客户", {"customer_managers": [outsider_name], "agency_fee_due": 812.75, "official_fee_unreceived": -101.25, "bank_account": "COMPANY-RECYCLE-PRIVATE-BANK"}, department="上海分所", owner=outsider_name)
        assert call("GET", f"/customers?scope=mine&customer_name={urllib.parse.quote(company_recycle_record['title'])}")["total"] == 1
        deleted_from_mine = call("POST", f"/customers/{company_recycle_record['id']}/recycle", {"comment": "我的客户：客户删除"})
        assert deleted_from_mine["status"] == "已回收"
        company_recycle_record = deleted_from_mine
        assert call("GET", f"/customers?scope=mine&customer_name={urllib.parse.quote(company_recycle_record['title'])}")["total"] == 0
        deleted_personal_recycle = call("GET", f"/customers?scope=recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}")
        assert any(item["id"] == company_recycle_record["id"] for item in deleted_personal_recycle["items"])
        forged_create_system_fields = {
            "notes": [{"id": "forged", "created_at": "2099-01-01T00:00:00"}],
            "last_contact_at": "2099-01-01T00:00:00", "contact_count": 999,
            "last_modified_by": manager_name, "last_modified_date": "2099-01-01",
            "status_before_recycle": "公海", "recycled_at": "2099-01-02T00:00:00", "recycled_by": manager_name,
            "restored_at": "2099-01-03T00:00:00", "restored_by": manager_name,
            "released_at": "2099-01-04T00:00:00", "released_by": manager_name,
            "claimed_at": "2099-01-05T00:00:00", "claimed_by": manager_name,
            "shared_with": [member_name], "is_shared": "是", "shared_at": "2099-01-06T00:00:00",
            "customer_managers": [outsider_name], "agency_fee_due": 13.25,
        }
        forged_create_record = call("POST", "/customers", {
            "serial_no": f"{serial('CUSTOMER-SYSTEM-INJECTION')}-{uuid.uuid4().hex[:4]}",
            "title": "范围客户创建系统字段注入",
            "status": "潜在", "owner": outsider_name, "department": "上海分所",
            "is_shared": True, "data": forged_create_system_fields,
        }, expected=(201,))
        records.append(forged_create_record["id"])
        assert forged_create_record["data"]["last_modified_by"] == USERNAME
        assert forged_create_record["data"]["shared_with"] == [] and forged_create_record["data"]["is_shared"] == "否"
        for forbidden_create_key in set(forged_create_system_fields) - {"last_modified_by", "shared_with", "is_shared", "customer_managers", "agency_fee_due"}:
            assert forbidden_create_key not in forged_create_record["data"]
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(forged_create_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote(forged_create_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(forged_create_record['title'])}")["total"] == 0
        recent_member_record = create_record("customer", "跟进中", "范围最近联系A", {"customer_managers": [member_name], "agency_fee_due": 601.25, "official_fee_unreceived": -70.5, "bank_account": "RECENT-PRIVATE-BANK", "last_contact_at": "2099-01-01T00:00:00", "contact_count": 99}, department="深圳分所", owner=member_name)
        recent_outsider_record = create_record("customer", "跟进中", "范围最近联系B", {"customer_managers": [outsider_name], "agency_fee_due": 701.5, "official_fee_unreceived": -80.75}, department="上海分所", owner=outsider_name)
        recent_contact_only_record = create_record("customer", "跟进中", "范围新增联系人不算联系", {"customer_managers": [member_name]}, department="深圳分所", owner=member_name)
        recent_update_first = create_record("customer", "跟进中", "范围最近更新A", {"customer_managers": [member_name], "agency_fee_due": 101.25, "official_fee_unreceived": -11.5, "last_modified_by": outsider_name, "last_modified_date": "2099-01-01"}, department="深圳分所", owner=member_name)
        recent_update_second = create_record("customer", "跟进中", "范围最近更新B", {"customer_managers": [member_name], "agency_fee_due": 202.5, "official_fee_unreceived": -22.75}, department="深圳分所", owner=member_name)
        recent_update_recycled = create_record("customer", "跟进中", "范围最近更新已回收", {"customer_managers": [member_name], "agency_fee_due": 303.75, "official_fee_unreceived": -33.25}, department="深圳分所", owner=member_name)
        recent_update_public = create_record("customer", "跟进中", "范围最近更新公海排除", {"customer_managers": [outsider_name], "agency_fee_due": 404.0, "official_fee_unreceived": -44.0}, department="上海分所", owner=outsider_name)
        recent_update_other_actor = create_record("customer", "跟进中", "范围最近更新他人修改", {"customer_managers": [outsider_name], "agency_fee_due": 505.0, "official_fee_unreceived": -55.0}, department="上海分所", owner=outsider_name)
        assert recent_update_first["data"]["last_modified_by"] == USERNAME
        assert "last_modified_date" not in recent_update_first["data"]
        call("POST", f"/customers/{recent_update_recycled['id']}/recycle", {"comment": "最近更新必须包含当前人回收的客户"})
        public_contact_log = call("POST", "/communications", {"customer_record_id": recent_update_public["id"], "contact": "公海前联系人", "content": "进入公海后不得留在最近联系", "occurred_at": datetime.now().isoformat(timespec="seconds")}, expected=(201,)); communications.append(public_contact_log["id"])
        assert call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote(recent_update_public['title'])}")["total"] == 1
        call("POST", f"/customers/{recent_update_public['id']}/release", {"comment": "最近更新必须隔离公海客户"})
        assert call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote(recent_update_public['title'])}")["total"] == 0
        TOKEN = login(outsider_name, "SmokePass2026!")["access_token"]
        other_actor_saved = call("PATCH", f"/records/{recent_update_other_actor['id']}", {"description": "由其他用户在同日修改"})
        assert other_actor_saved["data"]["last_modified_by"] == outsider_name
        outsider_recent_update = call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote('范围最近更新')}")
        assert outsider_recent_update["total"] == 1 and outsider_recent_update["items"][0]["id"] == recent_update_other_actor["id"]
        assert call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote(recent_update_first['title'])}")["total"] == 0
        TOKEN = login(auditor_name, "SmokePass2026!")["access_token"]
        call("GET", "/customers?scope=recent_update", expected=(403,))
        call("GET", "/customers?scope=company_recycle", expected=(403,))
        call("GET", f"/customers/conflicts?name={urllib.parse.quote('任意完整企业名称')}", expected=(403,))
        TOKEN = admin_token
        current_user_permission = next(item for item in call("GET", "/system/role-permissions")["items"] if item["role"] == "user")
        try:
            without_conflict_leaf = [key for key in current_user_permission["menu_keys"] if key != "customer-conflict"]
            call("PATCH", "/system/role-permissions/user", {
                "data_scope": current_user_permission["data_scope"],
                "menu_keys": without_conflict_leaf,
                "field_keys": current_user_permission["field_keys"],
            })
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            call("GET", f"/customers/conflicts?name={urllib.parse.quote('任意完整企业名称')}", expected=(403,))
        finally:
            TOKEN = admin_token
            call("PATCH", "/system/role-permissions/user", {
                "data_scope": current_user_permission["data_scope"],
                "menu_keys": current_user_permission["menu_keys"],
                "field_keys": current_user_permission["field_keys"],
            })
        call("PATCH", f"/records/{recent_update_first['id']}", {"data": {"last_modified_by": outsider_name}}, expected=(409,))
        call("PATCH", f"/records/{recent_update_recycled['id']}", {"description": "回收客户较早更新，仍应计入但不排第一"})
        time.sleep(1.1)
        call("PATCH", f"/records/{recent_update_first['id']}", {"description": "当前管理员更新 A，作为第二条稳定样本"})
        time.sleep(1.1)
        call("PATCH", f"/records/{recent_update_second['id']}", {"description": "当前管理员最后更新 B，应排第一"})
        recent_update_page = call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote('范围最近更新')}&customer_type={urllib.parse.quote('客户')}&page=1&page_size=1")
        assert recent_update_page["total"] == 3 and recent_update_page["page"] == 1 and recent_update_page["page_size"] == 1, recent_update_page
        assert recent_update_page["items"][0]["id"] == recent_update_second["id"]
        assert recent_update_page["summary"] == {"agency_fee_due": 607.5, "official_fee_unreceived": -67.5}
        stable_second_page = call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote('范围最近更新')}&page=2&page_size=1")
        assert stable_second_page["items"][0]["id"] == recent_update_first["id"]
        assert call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote(recent_update_first['title'])}&manager={urllib.parse.quote(member_name)}")["total"] == 1
        assert call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote(recent_update_first['title'])}&manager={urllib.parse.quote(outsider_name)}")["total"] == 0
        assert call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote('范围最近更新')}&customer_type={urllib.parse.quote('当事人')}")["total"] == 0
        assert call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote(recent_update_public['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote(recent_update_other_actor['title'])}")["total"] == 0
        reordered_update = call("PATCH", f"/records/{recent_update_first['id']}", {"description": "当前管理员再次编辑后应升至第一位"})
        assert reordered_update["data"]["last_modified_by"] == USERNAME and "last_modified_date" not in reordered_update["data"]
        assert call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote(recent_update_first['title'])}")["items"][0]["id"] == recent_update_first["id"]
        # Protected recency fields supplied during creation are ignored.
        forged_recent = call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote(recent_member_record['title'])}")
        assert forged_recent["total"] == 0
        added_directory_contact = call("POST", f"/customers/{recent_contact_only_record['id']}/contacts", {"name": "仅新增联系人", "phone": "13800000009"}, expected=(201,))
        assert call("GET", f"/records/{recent_contact_only_record['id']}")["data"].get("last_contact_at", "") == ""
        assert call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote(recent_contact_only_record['title'])}")["total"] == 0
        recent_oldest_at = (datetime.now() - timedelta(days=4)).replace(microsecond=0)
        recent_middle_at = (datetime.now() - timedelta(days=3)).replace(microsecond=0)
        recent_latest_at = (datetime.now() - timedelta(days=2)).replace(microsecond=0)
        recent_oldest = call("POST", "/communications", {"customer_record_id": recent_member_record["id"], "contact": "旧联系人", "content": "最近联系旧记录", "occurred_at": recent_oldest_at.isoformat()}, expected=(201,)); communications.append(recent_oldest["id"])
        recent_middle = call("POST", "/communications", {"customer_record_id": recent_outsider_record["id"], "contact": "外部联系人", "content": "最近联系中间记录", "occurred_at": recent_middle_at.isoformat()}, expected=(201,)); communications.append(recent_middle["id"])
        recent_latest = call("POST", "/communications", {"customer_record_id": recent_member_record["id"], "contact": "新联系人", "content": "最近联系最新记录", "occurred_at": recent_latest_at.isoformat()}, expected=(201,)); communications.append(recent_latest["id"])
        admin_recent_page = call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote('范围最近联系')}&customer_type={urllib.parse.quote('客户')}&page=1&page_size=1")
        assert admin_recent_page["total"] == 2 and admin_recent_page["page"] == 1 and admin_recent_page["page_size"] == 1
        assert admin_recent_page["items"][0]["id"] == recent_member_record["id"]
        assert admin_recent_page["summary"] == {"agency_fee_due": 1302.75, "official_fee_unreceived": -151.25}
        assert admin_recent_page["items"][0]["data"]["bank_account"] == "RECENT-PRIVATE-BANK"
        assert call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote(recent_member_record['title'])}&manager={urllib.parse.quote(member_name)}")["total"] == 1
        assert call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote(recent_member_record['title'])}&manager={urllib.parse.quote(outsider_name)}")["total"] == 0
        assert call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote('范围最近联系')}&customer_type={urllib.parse.quote('当事人')}")["total"] == 0
        # Moving the newest event backwards must expose the true maximum of
        # the remaining events instead of the most recently edited row.
        moved_latest_at = (datetime.now() - timedelta(days=5)).replace(microsecond=0)
        call("PATCH", f"/communications/{recent_latest['id']}", {"occurred_at": moved_latest_at.isoformat()})
        reordered_recent = call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote('范围最近联系')}&page=1&page_size=2")
        assert [item["id"] for item in reordered_recent["items"]] == [recent_outsider_record["id"], recent_member_record["id"]]
        assert reordered_recent["items"][1]["data"]["last_contact_at"] == recent_oldest_at.isoformat()
        assert reordered_recent["items"][1]["data"]["contact_count"] == 2
        recent_before_generic_patch = call("GET", f"/records/{recent_member_record['id']}")["data"]
        generic_customer_data = {
            key: value for key, value in recent_before_generic_patch.items()
            if key not in {"notes", "last_contact_at", "contact_count"}
        }
        generic_customer_data["cooperation_status"] = "通用资料修改不得清空联系统计"
        call("PATCH", f"/records/{recent_member_record['id']}", {"data": generic_customer_data})
        recent_after_omission = call("GET", f"/records/{recent_member_record['id']}")["data"]
        assert all(recent_after_omission.get(key) == recent_before_generic_patch.get(key) for key in {"notes", "last_contact_at", "contact_count"})
        for protected_key, forged_value in {
            "notes": [], "last_contact_at": "2099-01-01T00:00:00Z", "contact_count": 999,
        }.items():
            forged_data = dict(generic_customer_data); forged_data[protected_key] = forged_value
            call("PATCH", f"/records/{recent_member_record['id']}", {"data": forged_data}, expected=(409,))
        recent_after_injection = call("GET", f"/records/{recent_member_record['id']}")["data"]
        assert all(recent_after_injection.get(key) == recent_before_generic_patch.get(key) for key in {"notes", "last_contact_at", "contact_count"})

        timezone_rows = []
        for suffix_label, occurred_at in [
            ("A", "2020-01-01T10:00:00+08:00"),
            ("B", "2020-01-01T03:00:00Z"),
            ("C", "2020-01-01T02:30:00"),
        ]:
            timezone_record = create_record("customer", "跟进中", f"范围最近时区{suffix_label}", {"customer_managers": [member_name]}, department="深圳分所", owner=member_name)
            timezone_rows.append(timezone_record)
            timezone_communication = call("POST", "/communications", {"customer_record_id": timezone_record["id"], "contact": f"时区联系人{suffix_label}", "content": f"混合时区排序{suffix_label}", "occurred_at": occurred_at}, expected=(201,))
            communications.append(timezone_communication["id"])
        timezone_page = call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote('范围最近时区')}&page=1&page_size=15")
        assert [item["id"] for item in timezone_page["items"]] == [timezone_rows[1]["id"], timezone_rows[2]["id"], timezone_rows[0]["id"]]
        hidden_attachment = multipart_upload("/attachments", {"record_id": hidden_record["id"], "category": "普通附件", "remark": "越权隔离验证"}, f"hidden-{suffix}.txt", b"private smoke attachment")
        attachments.append(hidden_attachment["id"])
        shared_attachment = multipart_upload("/attachments", {"record_id": shared_record["id"], "category": "客户资料", "remark": "共享只读附件"}, f"shared-{suffix}.txt", b"shared customer attachment")
        attachments.append(shared_attachment["id"])
        manager_shared_attachment = multipart_upload("/attachments", {"record_id": manager_shared_record["id"], "category": "客户资料", "remark": "跨部门共享只读附件"}, f"manager-shared-{suffix}.txt", b"shared read-only attachment")
        attachments.append(manager_shared_attachment["id"])
        admin_token = TOKEN
        TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
        manager_ids = {item["id"] for item in call("GET", "/records?module=customer&page_size=100")["items"]}
        assert beijing_record["id"] in manager_ids and manager_shared_record["id"] in manager_ids and shanghai_record["id"] not in manager_ids
        call("GET", f"/records/{shanghai_record['id']}", expected=(404,))
        assert call("GET", f"/records/{manager_shared_record['id']}")["id"] == manager_shared_record["id"]
        assert any(item["id"] == manager_shared_attachment["id"] for item in call("GET", f"/attachments?record_id={manager_shared_record['id']}")["items"])
        assert call("GET", f"/attachments/{manager_shared_attachment['id']}/download", raw=True)[0] == 200
        call("PATCH", f"/records/{manager_shared_record['id']}", {"description": "跨部门共享保持只读"}, expected=(403,))
        manager_shared_page = call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(manager_shared_record['title'])}&customer_type={urllib.parse.quote('客户')}&page=1&page_size=15")
        assert manager_shared_page["total"] == 1 and manager_shared_page["items"][0]["id"] == manager_shared_record["id"]
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(beijing_record['title'])}")["total"] == 0
        TOKEN = login(member_name, "SmokePass2026!")["access_token"]
        call("GET", "/customers?scope=department", expected=(403,))
        call("GET", "/customers?scope=department_recycle", expected=(403,))
        call("GET", "/customers?scope=company", expected=(403,))
        public_page = call("GET", "/customers?scope=public&page=1&page_size=1")
        assert public_page["page"] == 1 and public_page["page_size"] == 1 and public_page["total"] >= 3
        assert len(public_page["items"]) == 1
        exact_public = call("GET", f"/customers?scope=public&customer_name={urllib.parse.quote(public_record['title'])}&customer_type={urllib.parse.quote('客户')}&page_size=15")
        assert exact_public["total"] == 1 and exact_public["items"][0]["id"] == public_record["id"]
        assert exact_public["summary"] == {"agency_fee_due": 800.75, "official_fee_unreceived": -120.5}
        assert "bank_account" not in exact_public["items"][0]["data"]
        assert call("GET", f"/customers?scope=public&customer_name={urllib.parse.quote(public_record['title'])}&customer_type={urllib.parse.quote('当事人')}")["total"] == 0
        assert call("GET", f"/customers?scope=public&customer_name={urllib.parse.quote(beijing_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=public&customer_name={urllib.parse.quote(department_recycle_substring_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=public&customer_name={urllib.parse.quote(public_record['title'])}&manager={urllib.parse.quote(outsider_name)}")["total"] == 1
        assert call("GET", f"/customers?scope=public&customer_name={urllib.parse.quote(public_substring_record['title'])}&manager={urllib.parse.quote(manager_name)}")["total"] == 0
        shared_page = call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_record['title'])}&customer_type={urllib.parse.quote('客户')}&page=1&page_size=1")
        assert shared_page["page"] == 1 and shared_page["page_size"] == 1 and shared_page["total"] == 1
        assert len(shared_page["items"]) == 1 and shared_page["items"][0]["id"] == shared_record["id"]
        assert shared_page["summary"] == {"agency_fee_due": 901.25, "official_fee_unreceived": -131.5}
        assert "bank_account" not in shared_page["items"][0]["data"]
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_record['title'])}&customer_type={urllib.parse.quote('当事人')}")["total"] == 0
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_record['title'])}&manager={urllib.parse.quote(outsider_name)}")["total"] == 1
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_record['title'])}&manager={urllib.parse.quote(member_name)}")["total"] == 0
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(own_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_substring_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_release_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_recycle_record['title'])}")["total"] == 0
        member_recent = call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote('范围最近联系')}&page=1&page_size=15")
        assert member_recent["total"] == 1 and member_recent["items"][0]["id"] == recent_member_record["id"]
        assert "bank_account" not in member_recent["items"][0]["data"]
        assert member_recent["items"][0]["data"]["last_contact_at"] == recent_oldest_at.isoformat()
        call("PATCH", f"/records/{public_member_record['id']}", {"description": "未领取不得修改公海客户"}, expected=(403,))
        call("PUT", f"/customers/{public_member_record['id']}/managers", {"managers": [member_name]}, expected=(409,))
        call("POST", f"/customers/{public_member_record['id']}/recycle", {"comment": "未领取不得回收公海客户"}, expected=(403,))
        claimed_member_public = call("POST", f"/customers/{public_member_record['id']}/claim", {"comment": "本人领取公海客户"})
        assert claimed_member_public["owner"] == member_name and claimed_member_public["department"] == "深圳分所" and claimed_member_public["status"] == "潜在"
        call("POST", f"/customers/{public_member_record['id']}/claim", {"comment": "重复领取"}, expected=(409,))
        member_items = call("GET", "/records?module=customer&page_size=100")["items"]
        member_ids = {item["id"] for item in member_items}
        assert own_record["id"] in member_ids and shared_record["id"] in member_ids and public_record["id"] in member_ids and hidden_record["id"] not in member_ids
        assert substring_record["id"] not in member_ids and shared_substring_record["id"] not in member_ids
        member_own = next(item for item in member_items if item["id"] == own_record["id"])
        assert "bank_account" not in member_own["data"] and member_own["data"]["legal_representative"] == "可见法人"
        call("GET", f"/records/{hidden_record['id']}", expected=(404,))
        call("GET", f"/attachments?record_id={hidden_record['id']}", expected=(404,))
        call("GET", f"/attachments/{hidden_attachment['id']}/download", expected=(404,))
        assert call("GET", f"/records/{shared_record['id']}")["id"] == shared_record["id"]
        assert any(item["id"] == shared_attachment["id"] for item in call("GET", f"/attachments?record_id={shared_record['id']}")["items"])
        assert call("GET", f"/attachments/{shared_attachment['id']}/download", raw=True)[0] == 200
        hidden_search = call("GET", f"/search?q={urllib.parse.quote(f'hidden-{suffix}')}")
        assert all(item.get("id") != hidden_attachment["id"] for item in hidden_search["items"])
        call("PATCH", f"/records/{shared_record['id']}", {"description": "共享用户不得修改"}, expected=(403,))
        call("POST", f"/customers/{shared_record['id']}/recycle", {"comment": "共享用户不得修改"}, expected=(403,))
        call("POST", f"/customers/{shared_record['id']}/release", {"comment": "共享用户不得释放"}, expected=(403,))
        call("POST", f"/customers/{shared_record['id']}/share", {"recipients": [manager_name], "comment": "共享用户不得二次共享"}, expected=(403,))
        call("PUT", f"/customers/{shared_record['id']}/managers", {"managers": [member_name]}, expected=(403,))
        call("POST", f"/customers/{shared_record['id']}/contacts", {"name": "共享用户不得新增联系人"}, expected=(403,))
        call("POST", f"/customers/{shared_record['id']}/notes", {"content": "共享用户不得新增跟进"}, expected=(403,))
        call("POST", "/communications", {"customer_record_id": shared_record["id"], "content": "共享用户不得新增沟通", "occurred_at": datetime.now().isoformat(timespec="seconds")}, expected=(403,))
        call("DELETE", f"/attachments/{shared_attachment['id']}", expected=(403,))
        multipart_upload("/attachments", {"record_id": shared_record["id"], "category": "客户资料", "remark": "共享只读不得上传"}, f"shared-denied-{suffix}.txt", b"forbidden", expected=(403,))
        assert call("GET", f"/customers/conflicts?name={urllib.parse.quote('范围隐藏客户')}")["found"] is False
        member_credit_code = f"91310000{suffix[-10:]}"
        member_created = call("POST", "/customers", {
            "title": f"SMOKE普通用户新建客户-{suffix}", "status": "潜在", "owner": USERNAME,
            "department": "北京分所", "customer_managers": [member_name, manager_name],
            "customer_type": "客户", "level": "立案客户", "is_shared": False, "is_assisted": "否",
            "fee_reduction": "no", "credit_code": member_credit_code,
            "data": {"agency_fee_due": 123.45, "official_fee_unreceived": -67.89},
        }, expected=(201,)); records.append(member_created["id"])
        assert member_created["serial_no"].startswith("KH")
        assert member_created["owner"] == member_name and member_created["department"] == "深圳分所"
        assert member_created["data"]["customer_managers"] == [member_name, manager_name]
        assert member_created["data"]["is_shared"] == "否" and member_created["data"]["fee_reduction"] == "否"
        mine_page = call("GET", "/customers?scope=mine&page=1&page_size=1")
        assert mine_page["page"] == 1 and mine_page["page_size"] == 1 and mine_page["total"] >= 2
        assert len(mine_page["items"]) == 1 and set(mine_page["summary"]) == {"agency_fee_due", "official_fee_unreceived"}
        exact_mine = call("GET", f"/customers?scope=mine&customer_name={urllib.parse.quote(member_created['title'])}&customer_type={urllib.parse.quote('客户')}&page_size=15")
        assert exact_mine["total"] == 1 and exact_mine["items"][0]["id"] == member_created["id"]
        assert exact_mine["summary"] == {"agency_fee_due": 123.45, "official_fee_unreceived": -67.89}
        exact_manager = call("GET", f"/customers?scope=mine&customer_name={urllib.parse.quote(member_created['title'])}&manager={urllib.parse.quote(member_name)}&page_size=15")
        assert exact_manager["total"] == 1 and exact_manager["items"][0]["id"] == member_created["id"]
        assert call("GET", f"/customers?scope=mine&customer_name={urllib.parse.quote(member_created['title'])}&manager={urllib.parse.quote(substring_manager_name)}&page_size=15")["total"] == 0
        assert call("GET", f"/customers?scope=mine&customer_name={urllib.parse.quote(member_created['title'])}&customer_type={urllib.parse.quote('当事人')}")["total"] == 0
        assert shared_record["id"] not in {item["id"] for item in call("GET", "/customers?scope=mine&page_size=200")["items"]}
        assert substring_record["id"] not in {item["id"] for item in call("GET", "/customers?scope=mine&page_size=200")["items"]}
        call("POST", "/customers", {"title": "", "owner": member_name}, expected=(422,))
        call("POST", "/customers", {"title": "SMOKE非法状态客户", "status": "跟进中", "owner": member_name}, expected=(422,))
        call("POST", "/customers", {"title": "SMOKE非法类型客户", "customer_type": "供应商", "owner": member_name}, expected=(422,))
        call("POST", "/customers", {"title": "SMOKE非法等级客户", "level": "重点客户", "owner": member_name}, expected=(422,))
        call("POST", "/customers", {"title": "SMOKE信用代码空格客户", "credit_code": "9131 0000", "owner": member_name}, expected=(422,))
        call("POST", "/customers", {"title": "SMOKE重复信用代码客户", "credit_code": member_credit_code.lower(), "owner": member_name}, expected=(409,))
        call("POST", "/customers", {"title": "SMOKE无效管理人客户", "owner": member_name, "customer_managers": [member_name, f"missing-{suffix}"]}, expected=(422,))
        call("POST", "/records", {"module": "customer", "serial_no": serial("CUSTOMER-BYPASS"), "title": "SMOKE通用入口绕过客户", "owner": member_name, "data": {"customer_managers": [member_name]}}, expected=(422,))
        call("PATCH", f"/records/{member_created['id']}", {"status": "公海"}, expected=(409,))
        member_document = multipart_upload("/attachments", {"record_id": member_created["id"], "category": "客户资料", "remark": "普通负责人附件权限"}, f"member-customer-{suffix}.txt", b"member document")
        attachments.append(member_document["id"])
        assert call("GET", f"/attachments/{member_document['id']}/download", raw=True)[0] == 200
        call("DELETE", f"/attachments/{member_document['id']}", expected=(204,)); attachments.remove(member_document["id"])
        import_title = f"SMOKE普通用户客户导入-{suffix}"
        import_csv = ("\ufeff客户名称,负责人,部门,联系人,电话,客户等级\r\n" + f"{import_title},{USERNAME},北京分所,导入联系人,13800000000,普通客户\r\n").encode("utf-8")
        imported_customer = multipart_upload("/customers/import", {}, f"customers-{suffix}.csv", import_csv, expected=(200,))
        assert imported_customer["created"] == 1 and imported_customer["failed"] == 0
        records.append(imported_customer["items"][0]["id"])
        assert imported_customer["items"][0]["owner"] == member_name and imported_customer["items"][0]["department"] == "深圳分所"
        imported_customer_detail = call("GET", f"/records/{imported_customer['items'][0]['id']}")
        assert imported_customer_detail["data"]["last_modified_by"] == member_name
        assert call("GET", f"/customers?scope=recent_update&customer_name={urllib.parse.quote(import_title)}")["total"] == 1
        TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
        call("GET", "/customers?scope=company", expected=(403,))
        call("GET", "/customers?scope=company_recycle", expected=(403,))
        manager_public = call("GET", f"/customers?scope=public&customer_name={urllib.parse.quote(beijing_public_record['title'])}&page_size=15")
        assert manager_public["total"] == 1 and manager_public["items"][0]["data"]["bank_account"] == "MANAGER-PUBLIC-BANK"
        call("PATCH", f"/records/{beijing_public_record['id']}", {"description": "原管理人不得修改公海客户"}, expected=(403,))
        department_page = call("GET", "/customers?scope=department&page=1&page_size=1")
        assert department_page["page"] == 1 and department_page["page_size"] == 1 and department_page["total"] >= 2
        assert len(department_page["items"]) == 1
        exact_department = call("GET", f"/customers?scope=department&customer_name={urllib.parse.quote(beijing_record['title'])}&customer_type={urllib.parse.quote('客户')}&page_size=15")
        assert exact_department["total"] == 1 and exact_department["items"][0]["id"] == beijing_record["id"]
        assert exact_department["summary"] == {"agency_fee_due": 300.25, "official_fee_unreceived": -40.5}
        assert call("GET", f"/customers?scope=department&customer_name={urllib.parse.quote(beijing_record['title'])}&customer_type={urllib.parse.quote('当事人')}")["total"] == 0
        assert call("GET", f"/customers?scope=department&customer_name={urllib.parse.quote(shanghai_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=department&customer_name={urllib.parse.quote(member_created['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=department&customer_name={urllib.parse.quote(beijing_public_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=department&customer_name={urllib.parse.quote(beijing_record['title'])}&manager={urllib.parse.quote(manager_name)}")["total"] == 1
        assert call("GET", f"/customers?scope=department&customer_name={urllib.parse.quote(department_substring_record['title'])}&manager={urllib.parse.quote(manager_name)}")["total"] == 0
        department_recycle_page = call("GET", "/customers?scope=department_recycle&page=1&page_size=1")
        assert department_recycle_page["page"] == 1 and department_recycle_page["page_size"] == 1 and department_recycle_page["total"] >= 2
        assert len(department_recycle_page["items"]) == 1
        exact_department_recycle = call("GET", f"/customers?scope=department_recycle&customer_name={urllib.parse.quote(department_recycle_record['title'])}&customer_type={urllib.parse.quote('客户')}&page_size=15")
        assert exact_department_recycle["total"] == 1 and exact_department_recycle["items"][0]["id"] == department_recycle_record["id"]
        assert exact_department_recycle["items"][0]["status"] == "已回收"
        assert exact_department_recycle["summary"] == {"agency_fee_due": 511.25, "official_fee_unreceived": -80.75}
        assert call("GET", f"/customers?scope=department_recycle&customer_name={urllib.parse.quote(department_recycle_record['title'])}&customer_type={urllib.parse.quote('当事人')}")["total"] == 0
        assert call("GET", f"/customers?scope=department_recycle&customer_name={urllib.parse.quote(outside_department_recycle_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=department_recycle&customer_name={urllib.parse.quote(department_recycle_record['title'])}&manager={urllib.parse.quote(department_peer_name)}")["total"] == 1
        assert call("GET", f"/customers?scope=department_recycle&customer_name={urllib.parse.quote(department_recycle_substring_record['title'])}&manager={urllib.parse.quote(manager_name)}")["total"] == 0
        call("PATCH", f"/records/{department_recycle_record['id']}", {"status": "潜在"}, expected=(409,))
        call("POST", f"/records/{beijing_public_record['id']}/transition", {"to_status": "跟进中", "comment": "通用客户流转旁路"}, expected=(409,))
        call("POST", f"/customers/{outside_department_recycle_record['id']}/restore", {"comment": "部门负责人不得恢复外部门客户"}, expected=(404,))
        call("POST", f"/customers/{outside_department_recycle_record['id']}/release", {"comment": "部门负责人不得释放外部门客户"}, expected=(404,))
        call("PUT", f"/customers/{shanghai_record['id']}/managers", {"managers": [manager_name], "comment": "部门负责人不得借公司客户入口跨部门分配"}, expected=(404,))
        restored_department_customer = call("POST", f"/customers/{department_recycle_record['id']}/restore", {"comment": "部门负责人恢复本部门客户"})
        assert restored_department_customer["status"] == "潜在"
        call("POST", f"/customers/{department_recycle_record['id']}/recycle", {"comment": "部门负责人再次回收本部门客户"})
        released_department_customer = call("POST", f"/customers/{department_recycle_record['id']}/release", {"comment": "部门回收站进入公海"})
        assert released_department_customer["status"] == "公海"
        department_assigned = call("PUT", f"/customers/{department_substring_record['id']}/managers", {"managers": [department_peer_name]})
        assert department_assigned["owner"] == department_peer_name and department_assigned["data"]["customer_managers"] == [department_peer_name]
        department_assignment_restored = call("PUT", f"/customers/{department_substring_record['id']}/managers", {"managers": [department_substring_manager_name]})
        assert department_assignment_restored["owner"] == department_substring_manager_name
        assert call("GET", f"/records/{member_created['id']}")["id"] == member_created["id"]
        manager_mine = call("GET", f"/customers?scope=mine&customer_name={urllib.parse.quote(member_created['title'])}&page_size=15")
        assert manager_mine["total"] == 1 and manager_mine["items"][0]["id"] == member_created["id"]
        manager_customer_note = call("POST", f"/customers/{member_created['id']}/notes", {"note_type": "权限验证", "content": "第二客户管理人可写"}, expected=(201,))
        assert manager_customer_note["content"] == "第二客户管理人可写"
        cross_department_csv = ("\ufeff客户名称,负责人,部门\r\n" + f"SMOKE跨部门导入拒绝-{suffix},{outsider_name},上海分所\r\n").encode("utf-8")
        rejected_customer_import = multipart_upload("/customers/import", {}, f"customers-cross-{suffix}.csv", cross_department_csv, expected=(200,))
        assert rejected_customer_import["created"] == 0 and rejected_customer_import["failed"] == 1
        TOKEN = login(member_name, "SmokePass2026!")["access_token"]
        assert call("GET", f"/customers/conflicts?name={urllib.parse.quote(member_created['title'])}")["found"] is False
        claimed_public = call("POST", f"/customers/{public_record['id']}/claim", {"comment": "领取公海客户"})
        assert claimed_public["owner"] == member_name and claimed_public["department"] == "深圳分所" and claimed_public["status"] == "潜在"
        TOKEN = admin_token
        call("DELETE", f"/communications/{recent_middle['id']}", expected=(204,)); communications.remove(recent_middle["id"])
        assert call("GET", f"/customers?scope=recent_contact&customer_name={urllib.parse.quote(recent_outsider_record['title'])}")["total"] == 0
        assert call("GET", f"/records/{recent_outsider_record['id']}")["data"]["contact_count"] == 0
        admin_public = call("GET", f"/customers?scope=public&customer_name={urllib.parse.quote(beijing_public_record['title'])}&page_size=15")
        assert admin_public["total"] == 1 and admin_public["items"][0]["data"]["bank_account"] == "MANAGER-PUBLIC-BANK"
        admin_shared = call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_record['title'])}&page_size=15")
        assert admin_shared["total"] == 1 and admin_shared["items"][0]["id"] == shared_record["id"]
        assert admin_shared["items"][0]["data"]["bank_account"] == "SHARED-PRIVATE-BANK"
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(manager_shared_record['title'])}")["total"] == 1
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_substring_record['title'])}")["total"] == 1
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(hidden_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_release_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=shared&customer_name={urllib.parse.quote(shared_recycle_record['title'])}")["total"] == 0
        company_page = call("GET", "/customers?scope=company&page=1&page_size=1")
        assert company_page["page"] == 1 and company_page["page_size"] == 1 and company_page["total"] >= 2
        assert len(company_page["items"]) == 1
        company_recycle_page = call("GET", "/customers?scope=company_recycle&page=1&page_size=1")
        assert company_recycle_page["page"] == 1 and company_recycle_page["page_size"] == 1 and company_recycle_page["total"] >= 2
        assert len(company_recycle_page["items"]) == 1
        exact_company_recycle = call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}&customer_type={urllib.parse.quote('客户')}&page_size=15")
        assert exact_company_recycle["total"] == 1 and exact_company_recycle["items"][0]["id"] == company_recycle_record["id"]
        assert exact_company_recycle["items"][0]["status"] == "已回收"
        assert exact_company_recycle["summary"] == {"agency_fee_due": 812.75, "official_fee_unreceived": -101.25}
        assert exact_company_recycle["items"][0]["data"]["bank_account"] == "COMPANY-RECYCLE-PRIVATE-BANK"
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}&customer_type={urllib.parse.quote('当事人')}")["total"] == 0
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}&manager={urllib.parse.quote(outsider_name)}")["total"] == 1
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}&manager={urllib.parse.quote('范围外人员')}")["total"] == 1
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}&manager={urllib.parse.quote(manager_name)}")["total"] == 0
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}&manager={urllib.parse.quote(outsider_name[1:-1])}")["total"] == 0
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}&manager={urllib.parse.quote('不存在的管理人姓名')}")["total"] == 0
        duplicate_display_user = call("POST", "/system/users", {"username": f"smoke_duplicate_display_{suffix}".lower(), "display_name": "范围外人员", "department": "上海分所", "password": "SmokePass2026!", "role": "user"}, expected=(201,))
        users.append(duplicate_display_user["id"])
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}&manager={urllib.parse.quote('范围外人员')}")["total"] == 0
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}&manager={urllib.parse.quote(outsider_name)}")["total"] == 1
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(beijing_record['title'])}")["total"] == 0
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(beijing_public_record['title'])}")["total"] == 0
        protected_customer_keys = {
            "notes", "last_contact_at", "contact_count", "last_modified_by", "last_modified_date",
            "status_before_recycle", "recycled_at", "recycled_by", "restored_at", "restored_by",
            "released_at", "released_by", "claimed_at", "claimed_by", "shared_with", "is_shared", "shared_at",
        }
        protected_baseline = dict(exact_company_recycle["items"][0]["data"])
        ordinary_customer_data = {
            key: value for key, value in protected_baseline.items()
            if key not in protected_customer_keys and key != "customer_managers"
        }
        ordinary_customer_data["short_name"] = "公司回收站安全资料编辑"
        ordinary_customer_saved = call("PATCH", f"/records/{company_recycle_record['id']}", {"data": ordinary_customer_data})
        assert ordinary_customer_saved["data"]["customer_managers"] == protected_baseline["customer_managers"]
        for protected_key in protected_customer_keys:
            assert (protected_key in ordinary_customer_saved["data"]) == (protected_key in protected_baseline)
            if protected_key in protected_baseline:
                assert ordinary_customer_saved["data"][protected_key] == protected_baseline[protected_key]
        protected_baseline = dict(ordinary_customer_saved["data"])
        lifecycle_forgery_attempts = {
            "status_before_recycle": "公海",
            "recycled_at": "2099-01-01T00:00:00",
            "recycled_by": manager_name,
            "restored_at": "2099-01-02T00:00:00",
            "restored_by": manager_name,
            "released_at": "2099-01-03T00:00:00",
            "released_by": manager_name,
            "claimed_at": "2099-01-04T00:00:00",
            "claimed_by": manager_name,
            "shared_with": [manager_name],
            "is_shared": "是",
            "shared_at": "2099-01-05T00:00:00",
        }
        for protected_key, forged_value in lifecycle_forgery_attempts.items():
            call("PATCH", f"/records/{company_recycle_record['id']}", {"data": {**protected_baseline, protected_key: forged_value}}, expected=(409,))
        call("PATCH", f"/records/{company_recycle_record['id']}", {"owner": manager_name}, expected=(409,))
        call("PATCH", f"/records/{company_recycle_record['id']}", {"data": {**protected_baseline, "customer_managers": [manager_name]}}, expected=(409,))
        protected_after_forgery = call("GET", f"/records/{company_recycle_record['id']}")
        assert protected_after_forgery["owner"] == outsider_name
        assert protected_after_forgery["data"] == protected_baseline
        call("PATCH", f"/records/{company_recycle_record['id']}", {"status": "潜在"}, expected=(409,))
        call("POST", f"/records/{company_recycle_record['id']}/transition", {"to_status": "潜在", "comment": "通用流转不得绕过公司回收站"}, expected=(409,))
        restored_company_customer = call("POST", f"/customers/{company_recycle_record['id']}/restore", {"comment": "公司回收站恢复客户"})
        assert restored_company_customer["status"] == "潜在"
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}")["total"] == 0
        call("POST", f"/customers/{company_recycle_record['id']}/recycle", {"comment": "公司客户再次回收"})
        released_company_customer = call("POST", f"/customers/{company_recycle_record['id']}/release", {"comment": "公司回收站进入公海"})
        assert released_company_customer["status"] == "公海"
        assert call("GET", f"/customers?scope=company_recycle&customer_name={urllib.parse.quote(company_recycle_record['title'])}")["total"] == 0
        exact_company = call("GET", f"/customers?scope=company&customer_name={urllib.parse.quote(beijing_record['title'])}&customer_type={urllib.parse.quote('客户')}&page_size=15")
        assert exact_company["total"] == 1 and exact_company["items"][0]["id"] == beijing_record["id"]
        assert exact_company["summary"] == {"agency_fee_due": 300.25, "official_fee_unreceived": -40.5}
        assert call("GET", f"/customers?scope=company&customer_name={urllib.parse.quote(beijing_record['title'])}&customer_type={urllib.parse.quote('当事人')}")["total"] == 0
        assert call("GET", f"/customers?scope=company&customer_name={urllib.parse.quote(beijing_public_record['title'])}")["total"] == 0
        company_recycled = call("GET", f"/customers?scope=company&customer_name={urllib.parse.quote(department_recycle_substring_record['title'])}&page=1&page_size=1")
        assert company_recycled["total"] == 1 and company_recycled["page"] == 1 and company_recycled["page_size"] == 1
        assert len(company_recycled["items"]) == 1 and company_recycled["items"][0]["id"] == department_recycle_substring_record["id"]
        assert company_recycled["items"][0]["status"] == "已回收"
        assert company_recycled["summary"] == {"agency_fee_due": 711.5, "official_fee_unreceived": -90.25}
        assert call("GET", f"/customers?scope=company&customer_name={urllib.parse.quote(beijing_record['title'])}&manager={urllib.parse.quote(manager_name)}")["total"] == 1
        assert call("GET", f"/customers?scope=company&customer_name={urllib.parse.quote(department_substring_record['title'])}&manager={urllib.parse.quote(manager_name)}")["total"] == 0
        company_sensitive = call("GET", f"/customers?scope=company&customer_name={urllib.parse.quote(own_record['title'])}&page_size=15")
        assert company_sensitive["total"] == 1 and company_sensitive["items"][0]["data"]["bank_account"] == "62220000"
        company_assigned = call("PUT", f"/customers/{shanghai_record['id']}/managers", {"managers": [manager_name], "comment": "管理员公司客户分配"})
        assert company_assigned["owner"] == manager_name and company_assigned["data"]["customer_managers"] == [manager_name]
        company_assignment_restored = call("PUT", f"/customers/{shanghai_record['id']}/managers", {"managers": [outsider_name], "comment": "恢复公司客户原管理人"})
        assert company_assignment_restored["owner"] == outsider_name
        admin_department_recycle = call("GET", f"/customers?scope=department_recycle&customer_name={urllib.parse.quote(outside_department_recycle_record['title'])}&page_size=15")
        assert admin_department_recycle["total"] == 1 and admin_department_recycle["items"][0]["id"] == outside_department_recycle_record["id"]
        restored_outside_department_customer = call("POST", f"/customers/{outside_department_recycle_record['id']}/restore", {"comment": "管理员恢复外部门回收客户"})
        assert restored_outside_department_customer["status"] == "潜在"
        call("POST", f"/customers/{outside_department_recycle_record['id']}/recycle", {"comment": "管理员再次回收外部门客户"})
        released_outside_department_customer = call("POST", f"/customers/{outside_department_recycle_record['id']}/release", {"comment": "管理员从部门回收站进入公海"})
        assert released_outside_department_customer["status"] == "公海"
        admin_department = call("GET", f"/customers?scope=department&customer_name={urllib.parse.quote(shanghai_record['title'])}&page_size=15")
        assert admin_department["total"] == 1 and admin_department["items"][0]["id"] == shanghai_record["id"]
        admin_hidden = call("GET", f"/customers?scope=mine&customer_name={urllib.parse.quote(hidden_record['title'])}&page_size=15")
        assert admin_hidden["total"] == 1 and admin_hidden["items"][0]["id"] == hidden_record["id"]
        admin_sensitive = call("GET", f"/customers?scope=mine&customer_name={urllib.parse.quote(own_record['title'])}&page_size=15")
        assert admin_sensitive["total"] == 1 and admin_sensitive["items"][0]["data"]["bank_account"] == "62220000"
        categories = call("GET", "/system/parameter-categories")["items"]
        assert len(categories) == 7 and any(item["key"] == "court" for item in categories)
        first_parameters = call("GET", "/system/parameters?category=court")
        second_parameters = call("GET", "/system/parameters?category=court")
        assert first_parameters["items"] and second_parameters["cached"] is True
        parameter = call("POST", "/system/parameters", {"category": "court", "code": f"SMOKE-{suffix}", "name": f"冒烟测试法院-{suffix}", "extra": {}, "sort_order": 9999, "is_active": True}, expected=(201,))
        system_parameters.append(parameter["id"])
        call("POST", "/system/parameters", {"category": "court", "code": f"SMOKE-{suffix}", "name": "重复法院", "extra": {}, "sort_order": 9999, "is_active": True}, expected=(409,))
        parameter = call("PATCH", f"/system/parameters/{parameter['id']}", {"name": f"冒烟测试法院已更新-{suffix}", "is_active": False})
        assert parameter["is_active"] is False and "已更新" in parameter["name"]
        configs = call("GET", "/system/configs")["items"]
        system_configs_original = {item["key"]: item["value"] for item in configs}
        assert "bank_address" in system_configs_original["company_profile"]
        company_profile = dict(system_configs_original["company_profile"]); company_profile["bank_address"] = "冒烟测试开户行地址"
        assert call("PATCH", "/system/configs/company_profile", {"value": company_profile})["value"]["bank_address"] == "冒烟测试开户行地址"
        share_policy = dict(system_configs_original["customer_share_policy"]); share_policy["all_days"] += 1
        assert call("PATCH", "/system/configs/customer_share_policy", {"value": share_policy})["value"]["all_days"] == share_policy["all_days"]
        call("PATCH", "/system/configs/customer_share_policy", {"value": {"all_days": 1}}, expected=(422,))
        application = dict(system_configs_original["application_settings"]); application["page_size"] = 30
        assert call("PATCH", "/system/configs/application_settings", {"value": application})["value"]["page_size"] == 30
        for key, value in system_configs_original.items(): call("PATCH", f"/system/configs/{key}", {"value": value})
        system_configs_original = {}
        cache = call("GET", "/system/caches")["items"][0]
        assert cache["key"] == "system-parameters"
        assert call("POST", "/system/caches/system-parameters/clear")["cleared"] is True
        menus = call("GET", "/system/menus")["items"]
        assert len(menus) >= 264 and any(item["key"] == "dashboard" for item in menus)
        navigation = call("GET", "/system/menus/navigation")["items"]
        assert len(navigation) >= 263
        assert any(item["key"] == "case-company-stage" and item["parent_key"] == "case-company" for item in navigation)
        assert any(item["key"] == "platform-finance-payment-waiting" and item["parent_key"] == "platform-finance-payment" for item in navigation)
        finance_children = sorted(
            (item for item in navigation if item["parent_key"] == "finance"),
            key=lambda item: item["sort_order"],
        )
        assert [(item["key"], item["label"]) for item in finance_children] == [
            ("finance-receipts", "回款管理"),
            ("finance-payment", "付款管理"),
            ("finance-internal", "内部费用"),
            ("finance-invoice", "开票管理"),
            ("finance-settlement", "结算管理"),
            ("finance-archive-fee", "归档费结算"),
            ("finance-fee-query", "费用查询"),
        ]
        platform_finance_children = sorted(
            (item for item in navigation if item["parent_key"] == "platform-finance"),
            key=lambda item: item["sort_order"],
        )
        assert [(item["key"], item["label"]) for item in platform_finance_children] == [
            ("platform-finance-overview", "回款管理"),
            ("platform-finance-payment", "付款管理"),
            ("platform-finance-invoice", "开票管理"),
            ("platform-finance-settlement", "结算管理"),
            ("platform-finance-archive-fee", "归档费结算"),
            ("platform-finance-fee-query", "费用查询"),
        ]
        assert [(item["key"], item["label"]) for item in sorted((item for item in navigation if item["parent_key"] == "hr"), key=lambda item: item["sort_order"])] == [
            ("hr-new", "新建员工"), ("hr-all", "员工管理"), ("hr-departments", "部门管理"), ("hr-roles", "角色管理"),
        ]
        assert [(item["key"], item["label"]) for item in sorted((item for item in navigation if item["parent_key"] == "system"), key=lambda item: item["sort_order"])] == [
            ("system-parameters", "系统参数"), ("system-management", "系统管理"),
        ]
        assert any(item["key"] == "warehouse-list" and item["parent_key"] == "warehouse" for item in navigation)
        call("POST", "/system/menus", {"key": f"smoke-menu-{suffix.lower()}", "parent_key": "system-management", "label": f"冒烟自定义菜单-{suffix}", "icon": "", "sort_order": 9999, "is_visible": True, "is_active": True}, expected=(422,))
        assert all(item["is_system"] for item in navigation)
        call("DELETE", f"/system/menus/{next(item for item in menus if item['key'] == 'dashboard')['id']}", expected=(422,))
        legacy_task_menus = [item for item in menus if item["key"] == "task-reminders"]
        assert all(item["is_visible"] is False and item["is_active"] is False for item in legacy_task_menus)
        assert all(item["key"] != "task-reminders" for item in call("GET", "/system/menus/navigation")["items"])
        dashboard_menu = next(item for item in menus if item["key"] == "dashboard")
        call("PATCH", f"/system/menus/{dashboard_menu['id']}", {"is_visible": False}, expected=(422,))
        call("DELETE", f"/system/parameters/{parameter['id']}", expected=(204,)); system_parameters.remove(parameter["id"])
        assert call("GET", "/hr/departments")["total"] >= 10 and call("GET", "/hr/job-roles")["total"] >= 5
        department = call("POST", "/hr/departments", {"code": f"SMK-{suffix[-8:]}", "name": f"冒烟部门-{suffix}", "manager": "冒烟负责人", "sort_order": 9999, "is_active": True}, expected=(201,)); departments.append(department["id"])
        call("POST", "/hr/departments", {"code": department["code"], "name": "重复部门", "sort_order": 9999, "is_active": True}, expected=(409,))
        role = call("POST", "/hr/job-roles", {"code": f"SMKROLE-{suffix[-8:]}", "name": f"冒烟岗位-{suffix}", "permissions": ["案件承办", "任务办理"], "description": "组织架构冒烟", "sort_order": 9999, "is_active": True}, expected=(201,)); job_roles.append(role["id"])
        call("POST", "/hr/job-roles", {"code": role["code"], "name": "重复岗位", "permissions": [], "sort_order": 9999, "is_active": True}, expected=(409,))
        organization_employee = create_record("hr", "在职", "冒烟组织员工", {"position": role["name"], "phone": "13800000000", "joined_at": str(date.today()), "employment_type": "全职"}, department=department["name"])
        department = call("PATCH", f"/hr/departments/{department['id']}", {"name": f"冒烟部门已更新-{suffix}", "manager": "新负责人"})
        role = call("PATCH", f"/hr/job-roles/{role['id']}", {"name": f"冒烟岗位已更新-{suffix}", "permissions": ["案件承办", "任务办理", "材料归档"]})
        propagated = call("GET", f"/records/{organization_employee['id']}")
        assert propagated["department"] == department["name"] and propagated["data"]["position"] == role["name"]
        call("DELETE", f"/hr/departments/{department['id']}", expected=(409,))
        call("DELETE", f"/hr/job-roles/{role['id']}", expected=(409,))
        call("DELETE", f"/records/{organization_employee['id']}", expected=(409,))
        call("DELETE", f"/testing/records/{organization_employee['id']}", expected=(204,)); records.remove(organization_employee["id"])
        call("DELETE", f"/hr/departments/{department['id']}", expected=(204,)); departments.remove(department["id"])
        call("DELETE", f"/hr/job-roles/{role['id']}", expected=(204,)); job_roles.remove(role["id"])
        passed("系统用户、安全策略、权限、系统参数配置、缓存及组织架构管理")

        import_rows = {
            "contract": (["业务编号", "合同名称", "客户/主体", "合同类型", "合同金额", "签订日期", "外部合同号", "负责人", "部门", "说明"], [serial("IMPORT-CONTRACT"), "冒烟导入合同", "冒烟导入客户", "专项服务", "10000.00", str(date.today()), serial("EXT"), USERNAME, "上海分所", suffix]),
            "case": (["业务编号", "案件名称", "关联合同号", "案件类型", "对方当事人", "法院", "负责人", "说明"], [serial("IMPORT-CASE"), "冒烟导入案件", "HT2026060097", "民事案件", "冒烟对方", "上海知识产权法院", USERNAME, suffix]),
            "task": (["业务编号", "任务内容", "客户/主体", "截止日期", "优先级", "来源", "关联案号", "负责人", "协作人", "部门", "说明"], [serial("IMPORT-TASK"), "冒烟导入任务", "冒烟导入客户", str(date.today() + timedelta(days=7)), "普通", "日常任务", "SH191000382B", USERNAME, f"{manager_name}、{member_name}", "上海分所", suffix]),
            "document": (["业务编号", "文件名称", "客户/主体", "收发类型", "文件日期", "关联案号", "来文/送达单位", "负责人", "部门", "说明"], [serial("IMPORT-DOC"), "冒烟导入收文", "光明乳业股份有限公司", "收文", str(date.today()), "SH191000382B", "上海市冒烟人民法院", USERNAME, "上海分所", suffix]),
            "finance": (["业务编号", "费用名称", "客户/主体", "费用类型", "金额", "关联案号", "经办人", "部门", "说明"], [serial("IMPORT-FEE"), "冒烟导入费用", "光明乳业股份有限公司", "官方费用", "88.80", "SH191000382B", USERNAME, "上海分所", suffix]),
            "hr": (["员工编号", "姓名", "状态", "部门", "岗位", "联系电话", "入职日期", "用工类型", "证件号码", "邮箱", "说明"], [serial("IMPORT-HR"), "冒烟导入员工", "试用", "上海分所", "律师助理", "13800000000", str(date.today()), "全职", "", "smoke@example.com", suffix]),
            "warehouse": (["物品编号", "物品名称", "物品类别", "数量", "单位", "存放位置", "部门", "供应商", "说明"], [serial("IMPORT-WH"), "冒烟导入物品", "电子设备", "1", "台", "冒烟仓 A-01", "上海分所", "冒烟供应商", suffix]),
            "seal": (["申请编号", "申请标题", "客户/主体", "印章编号", "份数", "用途", "计划日期", "办理方式", "文件名称", "负责人", "部门", "说明"], [serial("IMPORT-SEAL"), "冒烟导入用印", "冒烟导入客户", "YZ-GZ-001", "2", "接口验收", str(date.today() + timedelta(days=1)), "现场用印", "测试文件", USERNAME, "上海分所", suffix]),
        }
        for module, (headers, valid_row) in import_rows.items():
            if module == "case":
                call("GET", f"/records/import-template?module={module}", expected=(409,))
                content = ("\ufeff" + ",".join(headers) + "\r\n" + ",".join(valid_row) + "\r\n").encode("utf-8")
                multipart_upload(f"/records/import?module={module}", {}, f"{module}-{suffix}.csv", content, expected=(409,))
                continue
            template = call("GET", f"/records/import-template?module={module}", raw=True)
            assert template[1].startswith(b"\xef\xbb\xbf")
            invalid_row = ["" for _ in headers]
            content = ("\ufeff" + ",".join(headers) + "\r\n" + ",".join(valid_row) + "\r\n" + ",".join(invalid_row) + "\r\n").encode("utf-8")
            imported = multipart_upload(f"/records/import?module={module}", {}, f"{module}-{suffix}.csv", content, expected=(200,))
            assert imported["created"] == 1 and imported["failed"] == 1 and imported["errors"][0]["row"] == 3
            records.extend(item["id"] for item in imported["items"])
        task_headers = import_rows["task"][0]
        invalid_task_rows = [
            [serial("IMPORT-TASK-OWNER"), "无效负责人导入", "冒烟客户", str(date.today() + timedelta(days=2)), "普通", "日常任务", "", f"missing-{suffix}", member_name, "上海分所", suffix],
            [serial("IMPORT-TASK-COLLAB"), "无效协作人导入", "冒烟客户", str(date.today() + timedelta(days=2)), "普通", "日常任务", "", USERNAME, f"missing-{suffix}", "上海分所", suffix],
            [serial("IMPORT-TASK-DEADLINE"), "超期导入", "冒烟客户", str(date.today() + timedelta(days=31)), "普通", "日常任务", "", USERNAME, member_name, "上海分所", suffix],
            [serial("IMPORT-TASK-PRIORITY"), "无效优先级导入", "冒烟客户", str(date.today() + timedelta(days=2)), "最高", "日常任务", "", USERNAME, member_name, "上海分所", suffix],
        ]
        invalid_task_csv = ("\ufeff" + ",".join(task_headers) + "\r\n" + "\r\n".join(",".join(row) for row in invalid_task_rows) + "\r\n").encode("utf-8")
        rejected_task_import = multipart_upload("/records/import?module=task", {}, f"task-invalid-{suffix}.csv", invalid_task_csv, expected=(200,))
        assert rejected_task_import["created"] == 0 and rejected_task_import["failed"] == 4
        passed("合同、任务、收发文、费用、人事、仓库和用印 CSV 导入及案件通用导入旁路阻断")

        customer = create_record("customer", "跟进中", "冒烟测试客户")
        customer = call("PATCH", f"/records/{customer['id']}", {"data": {"level": "重点客户", "credit_code": "91310000SMOKE", "legal_representative": "测试法人", "invoice_title": "冒烟客户", "taxpayer_id": "91310000SMOKE", "bank_name": "测试银行", "bank_account": "622200001234"}})
        assert customer["data"]["legal_representative"] == "测试法人" and customer["data"]["bank_account"] == "622200001234"
        managed = call("PUT", f"/customers/{customer['id']}/managers", {"managers": [USERNAME, manager_name], "comment": "多客户管理人验收"})
        assert managed["owner"] == USERNAME and managed["data"]["customer_managers"] == [USERNAME, manager_name]
        communication = call("POST", "/communications", {"customer_record_id": customer["id"], "contact": "测试联系人", "phone": "13800000000", "content": f"冒烟沟通内容-{suffix}", "occurred_at": datetime.now().isoformat(timespec="seconds")}, expected=(201,)); communications.append(communication["id"])
        communication = call("PATCH", f"/communications/{communication['id']}", {"content": f"冒烟沟通内容已更新-{suffix}", "phone": "13900000000"})
        communication_keyword = urllib.parse.quote(f"已更新-{suffix}")
        assert any(item["id"] == communication["id"] for item in call("GET", f"/communications?keyword={communication_keyword}")["items"])
        customer_with_note = call("GET", f"/records/{customer['id']}")
        assert any(note.get("content") == communication["content"] and note.get("type") == "沟通日志" for note in customer_with_note["data"]["notes"])
        contact = call("POST", f"/customers/{customer['id']}/contacts", {"name": "测试联系人", "project_role": "项目负责人", "position": "法务经理", "phone": "13800000000", "office_phone": "021-60000000", "im_account": "test-im", "email": "contact@example.com", "contact_status": "正常联系", "is_valid": True, "is_primary": True}, expected=(201,))
        assert contact["project_role"] == "项目负责人" and contact["office_phone"] == "021-60000000" and contact["im_account"] == "test-im" and contact["contact_status"] == "正常联系" and contact["is_valid"] is True
        note = call("POST", f"/customers/{customer['id']}/notes", {"note_type": "电话沟通", "content": "冒烟测试客户跟进记录"}, expected=(201,))
        customer_document = multipart_upload("/attachments", {"record_id": customer["id"], "category": "客户资料", "remark": "客户文档验收"}, "customer-note.txt", b"customer document smoke")
        attachments.append(customer_document["id"])
        assert call("GET", f"/attachments?record_id={customer['id']}")["total"] >= 1
        share_member = call("POST", f"/customers/{customer['id']}/share", {"recipients": [member_name], "comment": "共享给成员"})
        share_outsider = call("POST", f"/customers/{customer['id']}/share", {"recipients": [outsider_name], "comment": "共享给其他成员"})
        concurrent_shares = [share_member, share_outsider]
        shared_customer = call("GET", f"/records/{customer['id']}")
        shared_recipients = set(shared_customer["data"]["shared_with"])
        if shared_recipients != {member_name, outsider_name}:
            call("POST", f"/customers/{customer['id']}/share", {"recipients": list({member_name, outsider_name} - shared_recipients), "comment": "并发共享补偿复核"})
            shared_customer = call("GET", f"/records/{customer['id']}")
        assert set(shared_customer["data"]["shared_with"]) == {member_name, outsider_name} and shared_customer["data"]["is_shared"] == "是"
        assert all(result["id"] == customer["id"] for result in concurrent_shares)
        shared_customer_again = call("POST", f"/customers/{customer['id']}/share", {"recipients": [member_name], "comment": "重复共享保持幂等"})
        assert set(shared_customer_again["data"]["shared_with"]) == {member_name, outsider_name}
        call("POST", f"/customers/{customer['id']}/share", {"recipients": [f"missing-{suffix}"], "comment": "不存在收件人"}, expected=(422,))
        call("POST", f"/customers/{customer['id']}/share", {"recipients": [USERNAME], "comment": "负责人无需共享给自己"}, expected=(422,))
        recycled_customer = call("POST", f"/customers/{customer['id']}/recycle", {"comment": "冒烟回收"})
        assert recycled_customer["data"]["shared_with"] == [] and recycled_customer["data"]["is_shared"] == "否"
        recycle_page = call("GET", f"/customers?scope=recycle&customer_name={urllib.parse.quote('冒烟测试客户')}&customer_type={urllib.parse.quote('客户')}&page=1&page_size=15")
        assert recycle_page["total"] == 1 and recycle_page["items"][0]["id"] == customer["id"]
        assert recycle_page["items"][0]["status"] == "已回收"
        released_from_recycle = call("POST", f"/customers/{customer['id']}/release", {"comment": "回收站进入公海"})
        assert released_from_recycle["status"] == "公海"
        claimed_from_public = call("POST", f"/customers/{customer['id']}/claim", {"comment": "回收站流程重新领取"})
        assert claimed_from_public["status"] == "潜在"
        call("POST", f"/customers/{customer['id']}/recycle", {"comment": "再次回收后恢复"})
        restored = call("POST", f"/customers/{customer['id']}/restore", {"comment": "冒烟恢复"})
        assert restored["status"] == "潜在"
        call("DELETE", f"/customers/{customer['id']}/contacts/{contact['id']}", expected=(204,))
        call("DELETE", f"/customers/{customer['id']}/notes/{note['id']}", expected=(204,))
        call("DELETE", f"/communications/{communication['id']}", expected=(204,)); communications.remove(communication["id"])
        assert all(note.get("content") != communication["content"] for note in call("GET", f"/records/{customer['id']}")["data"].get("notes", []))
        # 客户利益检索是全所最小披露：只按完整企业实体命中案件参与方，
        # 返回最新立案案件的原站八字段，不暴露记录 id 或旧风险列表。
        conflict_our_customer = f"SMOKE利益我方{suffix}有限公司"
        conflict_plaintiff = f"SMOKE利益原告（{suffix}）有限公司"
        conflict_defendant = f"SMOKE利益被告{suffix}有限公司"
        conflict_third_party = f"SMOKE利益第三人{suffix}有限公司"
        conflict_other_third_party = f"SMOKE利益其他第三人{suffix}有限公司"
        conflict_english_party = f"SMOKE Conflict {suffix}, Inc."
        create_record("customer", "跟进中", conflict_our_customer, {"customer_managers": [manager_name]}, department="北京分所", owner=manager_name)
        create_record("customer", "跟进中", conflict_plaintiff, {"customer_managers": [USERNAME]}, owner=USERNAME)
        create_record("customer", "跟进中", conflict_defendant, {"customer_managers": [outsider_name]}, owner=outsider_name)
        create_record("customer", "跟进中", conflict_third_party, {"customer_managers": [member_name]}, department="深圳分所", owner=member_name)
        create_record("customer", "跟进中", conflict_english_party, {"customer_managers": [manager_name]}, department="北京分所", owner=manager_name)
        conflict_contract = call("POST", "/contracts", {
            "module": "contract", "serial_no": serial("CONFLICT-CONTRACT"),
            "title": f"SMOKE利益检索合同-{suffix}", "customer": conflict_our_customer,
            "status": "已通过", "owner": USERNAME, "department": "上海分所", "data": {},
        }, expected=(201,)); records.append(conflict_contract["id"])
        call("POST", f"/contracts/{conflict_contract['id']}/submit", {"approvers": [manager_name], "comment": "利益检索测试合同审批"})
        conflict_contract = contract_approve_as(manager_name, conflict_contract["id"], True, "利益检索测试合同审批通过")

        def create_conflict_case(label: str, filing_date: str | None):
            created = call("POST", "/cases", {
                "contract_record_id": conflict_contract["id"],
                "serial_no": serial(f"CONFLICT-{label}"),
                "title": f"SMOKE利益检索案件-{label}-{suffix}",
                "status": "新案待分配", "owner": USERNAME, "case_type": "刑事案件",
                "cause_or_charge": "利益检索测试罪名", "handling_lawyers": [USERNAME],
                "client_position": "被告人/犯罪嫌疑人",
            }, expected=(201,))
            records.append(created["id"])
            call("PUT", f"/cases/{created['id']}/litigants", {
                "plaintiffs": [conflict_plaintiff],
                "defendants": [conflict_defendant, f"SMOKE利益共同被告{suffix}有限公司", conflict_english_party],
                "third_parties": [conflict_third_party, conflict_other_third_party],
                "comment": "利益检索当事人专用入口验收",
            })
            return call("PUT", f"/cases/{created['id']}/judicial", {
                "court": "测试法院", "filing_date": filing_date,
            })

        conflict_old_case = create_conflict_case("OLD", str(date.today() - timedelta(days=10)))
        conflict_same_date_earlier = create_conflict_case("SAME-A", str(date.today()))
        conflict_latest_case = create_conflict_case("SAME-B", str(date.today()))
        # Create the null-date record last so an incorrect created_at/id-only
        # implementation would select it; the dated case must still win.
        conflict_null_date_case = create_conflict_case("NULL", None)
        assert conflict_old_case["id"] < conflict_same_date_earlier["id"] < conflict_latest_case["id"] < conflict_null_date_case["id"]

        call("GET", f"/customers/conflicts?name={urllib.parse.quote('   ')}", expected=(422,))
        one_character = call("GET", f"/customers/conflicts?name={urllib.parse.quote('利')}")
        assert one_character["found"] is False and one_character["latest_case_date"] == ""
        partial_name = conflict_defendant.removesuffix("有限公司")
        assert call("GET", f"/customers/conflicts?name={urllib.parse.quote(partial_name)}")["found"] is False
        assert call("GET", f"/customers/conflicts?name={urllib.parse.quote(conflict_english_party.split(',')[0])}")["found"] is False

        expected_keys = {
            "found", "query", "enterprise_name", "latest_case_no", "latest_case_date",
            "plaintiffs", "defendants", "third_parties", "our_customer", "customer_managers",
        }
        expected_case_fields = {
            "latest_case_no": conflict_latest_case["serial_no"],
            "latest_case_date": str(date.today()),
            "plaintiffs": [conflict_plaintiff],
            "defendants": [conflict_defendant, f"SMOKE利益共同被告{suffix}有限公司", conflict_english_party],
            "third_parties": [conflict_third_party, conflict_other_third_party],
            "our_customer": conflict_our_customer,
        }
        role_expectations = [
            (conflict_our_customer, "范围经理"),
            (conflict_plaintiff.replace("（", "(").replace("）", ")"), profile["display_name"]),
            (conflict_defendant, "范围外人员"),
            (conflict_third_party, "范围成员"),
            (conflict_english_party, "范围经理"),
        ]
        for enterprise_name, expected_manager in role_expectations:
            result = call("GET", f"/customers/conflicts?name={urllib.parse.quote(enterprise_name)}")
            assert set(result) == expected_keys and result["found"] is True
            assert result["query"] == enterprise_name and result["enterprise_name"] == enterprise_name
            assert all(result[key] == value for key, value in expected_case_fields.items())
            assert result["customer_managers"] == [expected_manager]
            assert "id" not in result and "items" not in result and "risk" not in result

        TOKEN = login(member_name, "SmokePass2026!")["access_token"]
        whole_firm_result = call("GET", f"/customers/conflicts?name={urllib.parse.quote(conflict_defendant)}")
        assert whole_firm_result["found"] is True and whole_firm_result["latest_case_no"] == conflict_latest_case["serial_no"]
        assert "id" not in whole_firm_result and "items" not in whole_firm_result
        TOKEN = admin_token
        passed("客户多管理人、共享客户精确范围/字段权限/只读资源/并发共享/生命周期清权、最近联系排序/分页/重算、工商法务/开票银行资料、扩展联系人、跟进记录、客户文档、回收恢复和全所精确利益检索")

        aligned_customer = call("POST", "/customers", {
            "serial_no": serial("ALIGN-CUSTOMER"), "title": f"SMOKE蓝图客户-{suffix}", "status": "潜在",
            "owner": USERNAME, "department": "上海分所", "customer_managers": [USERNAME],
            "level": "潜在客户", "customer_type": "客户",
        }, expected=(201,)); records.append(aligned_customer["id"])
        call("POST", "/customers", {
            "serial_no": serial("ALIGN-CUSTOMER-DUP"), "title": f"  {aligned_customer['title']}  ", "status": "潜在",
            "owner": USERNAME, "department": "上海分所", "customer_managers": [USERNAME],
            "level": "潜在客户", "customer_type": "客户",
        }, expected=(409,))
        call("POST", f"/customers/{aligned_customer['id']}/key-change", {"title": f"SMOKE蓝图签约客户-{suffix}", "credit_code": f"91310000{suffix[-8:]}", "comment": "签约前核准客户主体"})
        aligned_customer = call("POST", f"/customers/{aligned_customer['id']}/key-change/review", {"approved": True, "comment": "客户主管核准主体"})
        call("POST", f"/customers/{aligned_customer['id']}/level-change", {"level": "签约客户", "comment": "合同签约后调整等级"})
        aligned_customer = call("POST", f"/customers/{aligned_customer['id']}/level-change/review", {"approved": True, "comment": "客户主管审批通过"})
        assert aligned_customer["data"]["level"] == "签约客户" and aligned_customer["data"]["key_change"]["status"] == "已通过"
        aligned_contract = call("POST", "/contracts", {
            "serial_no": serial("ALIGN-CONTRACT"), "title": f"SMOKE蓝图批量维权合同-{suffix}", "customer": aligned_customer["title"],
            "owner": USERNAME, "department": "上海分所", "description": "多外部合同号和客户服务端验收",
            "data": {"amount": 5000, "type": "批量维权合同", "external_contract_numbers": [f"EXT-A-{suffix}", f"EXT-B-{suffix}"]},
        }, expected=(201,)); records.append(aligned_contract["id"])
        assert aligned_contract["data"]["external_contract_numbers"] == [f"EXT-A-{suffix}", f"EXT-B-{suffix}"]
        call("POST", f"/contracts/{aligned_contract['id']}/submit", {"approvers": [manager_name], "comment": "蓝图合同审批"})
        contract_approve_as(manager_name, aligned_contract["id"], True, "蓝图合同审批通过")
        portal_document = multipart_upload("/attachments", {"record_id": aligned_contract["id"], "category": "客户可见合同", "remark": "客户服务端下载验收"}, f"smoke-portal-{suffix}.txt", b"portal document")
        attachments.append(portal_document["id"])
        portal = call("POST", f"/customers/{aligned_customer['id']}/portal/open", {"comment": "签约后开通客户服务端"})
        portal_credentials = {"account": portal["account"], "activation_code": portal["activation_code"]}
        portal_overview = call("POST", "/customer-portal/overview", portal_credentials)
        assert portal_overview["customer"]["level"] == "签约客户" and len(portal_overview["contracts"]) == 1 and portal_overview["documents"][0]["id"] == portal_document["id"]
        portal_download = call("POST", f"/customer-portal/files/{portal_document['id']}/download", portal_credentials, raw=True)
        assert portal_download[1] == b"portal document"
        portal_demand = call("POST", "/customer-portal/demands", {**portal_credentials, "title": f"SMOKE查询案件办理进展-{suffix}", "content": "请负责人反馈本周办理情况"}, expected=(201,)); records.append(portal_demand["id"])
        call("POST", f"/tasks/{portal_demand['id']}/accept", {"comment": "客户负责人接收需求"})
        call("POST", f"/tasks/{portal_demand['id']}/exception-request", {"action": "挂起", "reason": "等待客户补充案件材料"})
        suspended_demand = call("POST", f"/tasks/{portal_demand['id']}/exception-review", {"approved": True, "comment": "同意等待客户补充材料"})
        assert suspended_demand["workflow_status"] == "已停止" and suspended_demand["exception_request"]["status"] == "已通过"
        call("POST", f"/tasks/{portal_demand['id']}/restart", {"comment": "客户材料已经补充，恢复办理"})
        set_task_test_data(portal_demand["id"], {"deadline": str(date.today() - timedelta(days=2))})
        overdue_demand = next(item for item in call("GET", "/tasks?scope=company&page_size=200")["items"] if item["id"] == portal_demand["id"])
        assert overdue_demand["status"] == "已逾期" and overdue_demand["performance_impact"]["penalty_points"] == 2
        call("POST", f"/tasks/{portal_demand['id']}/complete", {"comment": "客户需求已经答复"})
        call("POST", f"/tasks/{portal_demand['id']}/confirm", {"comment": "客户负责人确认办结"})
        call("POST", f"/customers/{aligned_customer['id']}/portal/close", {"comment": "客户服务端停用验收"})
        call("POST", "/customer-portal/overview", portal_credentials, expected=(401,))
        passed("PDF 蓝图客户分级/关键字段审批、合同多外部编号、签约客户服务端、文档下载、客户需求任务、挂起审批及超期绩效闭环")

        call("POST", "/records", {"module": "contract", "serial_no": serial("CONTRACT-BYPASS"), "title": "绕过合同专用入口", "customer": "冒烟测试客户"}, expected=(422,))
        contract = create_record("contract", "草稿", "冒烟合同", {"amount": 1000, "external_contract_no": f"EXT-{suffix}"})
        call("PATCH", f"/records/{contract['id']}", {"status": "已通过", "title": "绕过合同审批"}, expected=(409,))
        call("POST", f"/records/{contract['id']}/transition", {"to_status": "审批中", "comment": "绕过合同专用审批"}, expected=(409,))
        call("DELETE", f"/records/{contract['id']}", expected=(409,))
        contract_attachment = multipart_upload("/attachments", {"record_id": contract["id"], "category": "合同附件", "remark": "合同向导附件验收"}, f"smoke-contract-{suffix}.txt", b"contract wizard attachment")
        attachments.append(contract_attachment["id"])
        call("POST", f"/contracts/{contract['id']}/submit", {"approvers": [USERNAME], "comment": "普通账号不得成为合同审批人"}, expected=(422,))
        call("POST", f"/contracts/{contract['id']}/submit", {"approvers": [manager_name, peer_manager_name], "comment": "合同不得选择多个审批人"}, expected=(422,))
        submitted = call("POST", f"/contracts/{contract['id']}/submit", {"approvers": [manager_name], "comment": "提交审核说明"})
        assert submitted["data"]["submitted_by"] == USERNAME and submitted["data"]["submit_comment"] == "提交审核说明"
        call("POST", f"/contracts/{contract['id']}/archive", expected=(409,))
        approval_state = call("GET", f"/contracts/{contract['id']}/approvals")
        assert [item["status"] for item in approval_state["items"]] == ["待审批"]
        assert approval_state["current_step"]["approver"] == manager_name
        assert any(item["id"] == contract_attachment["id"] for item in call("GET", f"/attachments?record_id={contract['id']}")["items"])
        sync_assets = call("GET", "/seals/assets")["items"]
        sync_asset = next(item for item in sync_assets if item["status"] == "可用")
        sync_linked_seal = call("POST", f"/contracts/{contract['id']}/seal-application", {"seal_asset_id": sync_asset["id"], "copies": 1, "purpose": "合同审批同步用印验收", "use_date": str(date.today() + timedelta(days=1)), "delivery_method": "现场用印", "document_names": "冒烟合同附件", "description": "合同审批完成后自动提交用印", "submit": False}, expected=(201,))
        records.append(sync_linked_seal["id"])
        sync_contract_state = call("GET", f"/records/{contract['id']}")
        assert sync_linked_seal["status"] == "草稿" and sync_contract_state["data"]["sync_seal"] is True
        call("POST", f"/contracts/{contract['id']}/approve", {"approved": True, "comment": "管理员不得代审"}, expected=(403,))
        first = contract_approve_as(manager_name, contract["id"], True, "角色审批通过")
        assert first["status"] == "已通过"
        sync_linked_seal = call("GET", f"/records/{sync_linked_seal['id']}")
        assert sync_linked_seal["status"] == "待审批" and sync_linked_seal["data"]["contract_no"] == contract["serial_no"]
        approval_state = call("GET", f"/contracts/{contract['id']}/approvals")
        assert approval_state["items"][0]["comment"] == "角色审批通过" and approval_state["items"][0]["acted_at"]
        assert approval_state["current_step"] is None
        contract_investigation = call("POST", f"/contracts/{contract['id']}/investigation", {"title": f"冒烟合同调查任务-{suffix}", "owner": "", "authorized_from": str(date.today()), "authorized_to": str(date.today() + timedelta(days=30)), "region": "上海市", "right_type": "商标", "customer_review": True, "description": "合同发起调查任务验收"}, expected=(201,))
        records.append(contract_investigation["id"])
        assert contract_investigation["module"] == "investigation" and contract_investigation["status"] == "待分配" and contract_investigation["data"]["contract_id"] == contract["id"]
        assigned_investigation = call("POST", f"/investigations/{contract_investigation['id']}/assign", {"investigator": USERNAME, "comment": "分配合同调查任务"})
        assert assigned_investigation["status"] == "进行中" and assigned_investigation["owner"] == USERNAME
        contract_investigation_task = call("POST", f"/investigations/{contract_investigation['id']}/tasks", {"title": "合同调查子任务", "owner": USERNAME, "deadline": str(date.today() + timedelta(days=10)), "priority": "普通", "description": "调查区域走访"}, expected=(201,))
        records.append(contract_investigation_task["id"])
        assert contract_investigation_task["investigation_record_id"] == contract_investigation["id"] and contract_investigation_task["investigation_module"] == "investigation"
        reloaded_subtasks = call("GET", f"/records?module=task&keyword={urllib.parse.quote(contract_investigation_task['serial_no'])}&page_size=100")["items"]
        reloaded_subtask = next(item for item in reloaded_subtasks if item["id"] == contract_investigation_task["id"])
        assert reloaded_subtask["data"]["investigation_record_id"] == contract_investigation["id"] and reloaded_subtask["data"]["investigation_module"] == "investigation"
        call("POST", f"/tasks/{contract_investigation_task['id']}/accept", {"comment": "执行合同调查子任务"})
        call("POST", f"/tasks/{contract_investigation_task['id']}/complete", {"comment": "调查区域走访完成"})
        call("POST", f"/tasks/{contract_investigation_task['id']}/confirm", {"comment": "调查主管验收通过"})
        closed_investigation = call("POST", f"/investigations/{contract_investigation['id']}/close", {"comment": "调查任务全部办结并形成报告"})
        assert closed_investigation["record"]["status"] == "已完成" and closed_investigation["report"]["category"] == "调查任务报告"
        attachments.append(closed_investigation["report"]["id"])
        contract_history = call("GET", f"/records/{contract['id']}/history")["items"]
        assert {"提交合同审批", "合同审批完成"}.issubset({item["action"] for item in contract_history})
        rejected_contract = create_record("contract", "草稿", "驳回续办冒烟合同", {"amount": 300})
        call("POST", f"/contracts/{rejected_contract['id']}/submit", {"approvers": [manager_name], "comment": "首次提交"})
        contract_approve_as(manager_name, rejected_contract["id"], False, "", expected=(422,))
        rejected = contract_approve_as(manager_name, rejected_contract["id"], False, "附件需要补正")
        assert rejected["status"] == "已拒绝"
        call("POST", f"/contracts/{rejected_contract['id']}/submit", {"approvers": [manager_name], "comment": "补正后重新提交"})
        assert contract_approve_as(manager_name, rejected_contract["id"], True, "补正通过")["status"] == "已通过"
        assert len(call("GET", f"/records/{rejected_contract['id']}/history")["items"]) >= 5
        changed = call("POST", f"/contracts/{contract['id']}/changes", {"change_type": "金额调整", "reason": "补充服务范围", "amount": 1200, "external_contract_no": f"EXT-CHANGED-{suffix}", "end_date": str(date.today() + timedelta(days=365))}, expected=(201,))
        assert changed["status"] == "待审批" and changed["contract"]["data"]["amount"] == 1000 and len(changed["changes"]) == 3
        changed = call("POST", f"/contracts/{contract['id']}/changes/review", {"approved": True, "comment": "合同管理员与财务主管审批通过"})
        assert changed["status"] == "已通过" and changed["contract"]["data"]["amount"] == 1200
        change_history = call("GET", f"/contracts/{contract['id']}/changes")
        assert change_history["total"] == 2 and all(item["reason"] == "补充服务范围" for item in change_history["items"])
        archive_contract = create_record("contract", "草稿", "归档冒烟合同", {"amount": 500})
        call("POST", f"/contracts/{archive_contract['id']}/submit", {"approvers": [manager_name], "comment": "归档前审批"})
        contract_approve_as(manager_name, archive_contract["id"], True, "审批通过")
        archived_contract = call("POST", f"/contracts/{archive_contract['id']}/archive")
        assert archived_contract["status"] == "已归档" and archived_contract["data"]["archived_at"]
        plan = call("POST", "/receivables", {"contract_record_id": contract["id"], "phase": "首期款", "due_date": str(date.today() + timedelta(days=10)), "amount": 1000, "payer": "冒烟客户"}, expected=(201,))
        receivables.append(plan["id"])
        call("POST", f"/receivables/{plan['id']}/receive", {"amount": 400, "comment": "部分回款"})
        call("POST", f"/receivables/{plan['id']}/receive", {"amount": 700, "comment": "超额"}, expected=(409,))
        complete_plan = call("POST", f"/receivables/{plan['id']}/receive", {"amount": 600, "comment": "尾款"})
        assert complete_plan["status"] == "已收款"
        call("DELETE", f"/receivables/{plan['id']}", expected=(204,)); receivables.remove(plan["id"])
        passed("合同向导附件、单一部长审批、普通账号/多人选择阻断、驳回续办、状态时间线、变更留痕和应收回款边界")

        eligible_contracts = call("GET", "/cases/eligible-contracts")
        assert any(item["id"] == contract["id"] for item in eligible_contracts["items"])
        assert all(item["status"] in {"已通过", "履行中", "已完成"} for item in eligible_contracts["items"])
        case_references = call("GET", "/cases/reference-options")
        assert {item["value"] for item in case_references["case_types"]} == {"民事案件", "刑事案件", "行政案件及国家赔偿", "法律顾问", "仲裁"}
        assert "侵害商标权纠纷" in {item["value"] for item in case_references["causes"]} and "商标权" in case_references["right_types"]
        call("POST", "/records", {"module": "case", "serial_no": serial("CASE-NO-CONTRACT"), "title": "无合同案件", "status": "新案待分配"}, expected=(422,))
        case_payload = {"contract_record_id": contract["id"], "serial_no": serial("CASE"), "title": "冒烟案件", "status": "新案待分配", "owner": USERNAME, "case_type": "刑事案件", "client_position": "被告人/犯罪嫌疑人", "cause_or_charge": "测试罪名", "handling_lawyers": [USERNAME], "court": "不应由第一步写入的法院"}
        civil_payload = {**case_payload, "serial_no": serial("CIVIL-CASE"), "title": "冒烟民事案件", "case_type": "民事案件", "client_position": "原告/申请人", "cause_or_charge": "侵害商标权纠纷", "right_type": "商标权"}
        civil_case = call("POST", "/cases", civil_payload, expected=(201,)); records.append(civil_case["id"])
        assert civil_case["data"]["case_type"] == "民事案件" and civil_case["data"]["right_type"] == "商标权"
        assert civil_case["data"]["source_person"] == (contract["data"].get("source_person") or contract["owner"])
        call("PUT", f"/cases/{civil_case['id']}/litigants", {"plaintiffs": ["冒烟民事原告"], "defendants": ["冒烟民事被告"], "comment": "民事当事人"})
        call("PUT", f"/cases/{civil_case['id']}/judicial", {"first_court_enabled": True, "first_court_name": "上海市民事测试人民法院", "first_court_case_no": serial("CIVIL-JUDICIAL")})
        civil_case = call("POST", f"/cases/{civil_case['id']}/creation/review", {"approved": True, "comment": "民事案件主管审核通过"})
        assert civil_case["status"] == "新案待分配" and civil_case["data"]["case_creation_approval_status"] == "已通过"
        team_assigned_case = call("POST", f"/cases/{civil_case['id']}/assign", {
            "customer_manager": member_name,
            "hearing_lawyer": member_name,
            "handling_lawyers": [member_name],
            "assistant": department_peer_name,
            "comment": "案件团队稳定用户名与分层权限验收",
        })
        assert team_assigned_case["data"]["handling_lawyer_usernames"] == [member_name]
        assert team_assigned_case["data"]["assistant_username"] == department_peer_name
        assert set(team_assigned_case["data"]["case_team_usernames"]) == {member_name, department_peer_name}
        call("POST", f"/cases/{civil_case['id']}/assign", {
            "customer_manager": member_name, "hearing_lawyer": member_name,
            "handling_lawyers": ["missing-case-team-user"], "assistant": department_peer_name,
        }, expected=(422,))
        TOKEN = login(member_name, "SmokePass2026!")["access_token"]
        assert call("GET", f"/records/{civil_case['id']}")["id"] == civil_case["id"]
        handling_capabilities = call("GET", f"/cases/{civil_case['id']}/action-capabilities")
        assert handling_capabilities["team_role"] == "handling_lawyer"
        assert all(handling_capabilities[key] is True for key in ["can_upload_attachment", "can_create_reminder", "can_create_log", "can_update_progress", "can_manage_hearing"])
        assert all(handling_capabilities[key] is False for key in ["can_assign_team", "can_close_case", "can_archive", "can_create_finance"])
        member_attachment = multipart_upload("/attachments", {"record_id": civil_case["id"], "category": "案件文档", "remark": "团队律师附件权限验收"}, f"smoke-case-team-{suffix}.txt", b"case team permission")
        call("DELETE", f"/attachments/{member_attachment['id']}", expected=(204,))
        member_progress = call("POST", f"/cases/{civil_case['id']}/progress", {"first_instance_court": "上海市团队权限测试法院", "first_instance_case_no": serial("TEAM-PROGRESS"), "comment": "受派经办律师登记进展"})
        assert member_progress["data"]["first_instance_case_no"]
        member_hearing = call("POST", "/hearings", {"case_record_id": civil_case["id"], "hearing_date": str(date.today() + timedelta(days=10)), "hearing_time": "10:00", "court": "上海市团队权限测试法院", "courtroom": "第一法庭", "hearing_type": "一审开庭", "hearing_lawyer": member_name}, expected=(201,))
        assert member_hearing["case_record_id"] == civil_case["id"]
        call("POST", f"/cases/{civil_case['id']}/assign", {"customer_manager": member_name, "hearing_lawyer": member_name, "handling_lawyers": [member_name]}, expected=(403,))
        TOKEN = login(department_peer_name, "SmokePass2026!")["access_token"]
        assert call("GET", f"/records/{civil_case['id']}")["id"] == civil_case["id"]
        assistant_capabilities = call("GET", f"/cases/{civil_case['id']}/action-capabilities")
        assert assistant_capabilities["team_role"] == "assistant"
        assert all(assistant_capabilities[key] is True for key in ["can_upload_attachment", "can_create_reminder", "can_create_log"])
        assert all(assistant_capabilities[key] is False for key in ["can_update_progress", "can_manage_hearing", "can_assign_team", "can_close_case", "can_archive", "can_create_finance"])
        assistant_reminder = call("POST", f"/cases/{civil_case['id']}/reminders", {"reminder_date": str(date.today()), "deadline": str(date.today() + timedelta(days=2)), "content": f"SMOKE-案件助理提醒-{suffix}"}, expected=(201,)); records.append(assistant_reminder["id"])
        call("POST", f"/cases/{civil_case['id']}/logs", {"content": f"SMOKE-案件助理日志-{suffix}"}, expected=(201,))
        call("POST", f"/cases/{civil_case['id']}/progress", {"first_instance_case_no": serial("ASSISTANT-BLOCK")}, expected=(403,))
        call("POST", "/hearings", {"case_record_id": civil_case["id"], "hearing_date": str(date.today() + timedelta(days=11)), "hearing_time": "10:00", "court": "上海市团队权限测试法院", "courtroom": "第二法庭", "hearing_type": "一审开庭", "hearing_lawyer": member_name}, expected=(403,))
        TOKEN = login(outsider_name, "SmokePass2026!")["access_token"]
        call("GET", f"/records/{civil_case['id']}", expected=(404,))
        TOKEN = admin_token
        passed("案件团队稳定用户名、经办律师可见/进展/排期/附件、助理详情办理限制与无关人员隔离")
        call("POST", "/cases", {**case_payload, "status": "执行"}, expected=(422,))
        call("POST", "/cases", {**case_payload, "owner": "不存在的案件负责人"}, expected=(422,))
        call("POST", "/cases", {**case_payload, "client_position": "原告"}, expected=(422,))
        call("POST", "/cases", {**case_payload, "handling_lawyers": ["不存在的经办律师"]}, expected=(422,))
        automatic_case_payload = {key: value for key, value in case_payload.items() if key not in {"serial_no", "court", "owner"}}
        automatic_case_a = call("POST", "/cases", {**automatic_case_payload, "title": "SMOKE服务端自动案号 A"}, expected=(201,))
        automatic_case_b = call("POST", "/cases", {**automatic_case_payload, "title": "SMOKE服务端自动案号 B"}, expected=(201,))
        records.extend([automatic_case_a["id"], automatic_case_b["id"]])
        assert automatic_case_a["serial_no"].startswith("SHXS") and len(automatic_case_a["serial_no"]) == 11 and automatic_case_a["serial_no"][4:].isdigit()
        assert automatic_case_b["serial_no"].startswith("SHXS") and len(automatic_case_b["serial_no"]) == 11 and automatic_case_b["serial_no"][4:].isdigit()
        assert automatic_case_a["serial_no"] != automatic_case_b["serial_no"]
        assert automatic_case_a["owner"] == USERNAME and automatic_case_b["owner"] == USERNAME
        case = call("POST", "/cases", case_payload, expected=(201,))
        records.append(case["id"])
        assert case["customer"] == contract["customer"] and case["data"]["contract_id"] == contract["id"] and case["data"]["contract_no"] == contract["serial_no"]
        assert case["status"] == "新案待分配" and case["department"] == contract["department"]
        assert case["data"]["case_creation_step"] == "basic" and "court" not in case["data"]
        call("POST", "/cases", case_payload, expected=(409,))
        assignment_payload = {"customer_manager": USERNAME, "hearing_lawyer": USERNAME, "handling_lawyers": [USERNAME], "assistant": USERNAME, "comment": "分配"}
        call("POST", f"/cases/{case['id']}/assign", assignment_payload, expected=(409,))
        call("PUT", f"/cases/{case['id']}/judicial", {"court": "上海市测试人民法院"}, expected=(409,))
        call("PUT", f"/cases/{case['id']}/litigants", {"defendants": ["过长" * 200]}, expected=(422,))
        litigants = call("PUT", f"/cases/{case['id']}/litigants", {
            "plaintiffs": ["上海市人民检察院"], "plaintiff_agents": ["公诉人甲"],
            "defendants": ["冒烟被告人"], "defendant_agents": ["辩护人甲"],
            "third_parties": ["冒烟被害人"], "third_party_agents": ["代理人甲"],
            "comment": "刑事案件当事人阶段",
        })
        assert litigants["data"]["case_creation_step"] == "litigants" and litigants["data"]["defendant_agents"] == ["辩护人甲"]
        call("PUT", f"/cases/{case['id']}/judicial", {"hearing_time": "25:61"}, expected=(422,))
        judicial = call("PUT", f"/cases/{case['id']}/judicial", {
            "court": "上海市测试人民法院", "court_case_no": serial("JUDICIAL-NO"),
            "judge": "测试法官", "clerk": "测试书记员", "judge_phone": "021-12345678",
            "filing_date": str(date.today()), "hearing_date": str(date.today() + timedelta(days=20)),
            "hearing_time": "09:30", "courtroom": "第一法庭", "judicial_remark": "司法机关阶段验收",
            "description": "刑事案件案情说明",
            "public_security_name": "上海市公安局测试分局", "public_security_case_no": serial("PS-NO"),
            "public_security_operator": "测试侦查员",
            "first_procuratorate_name": "上海市测试人民检察院", "first_procuratorate_operator": "测试检察官",
            "first_court_enabled": True, "first_court_name": "上海市测试人民法院",
            "first_court_case_no": serial("FIRST-JUDICIAL-NO"), "first_court_clerk": "测试书记员",
        })
        assert judicial["data"]["case_creation_step"] == "completed" and judicial["data"]["public_security_operator"] == "测试侦查员"
        assert judicial["status"] == "待立案审批" and judicial["data"]["case_creation_approval_status"] == "待审批"
        call("POST", f"/cases/{case['id']}/assign", assignment_payload, expected=(409,))
        case = call("POST", f"/cases/{case['id']}/creation/review", {"approved": True, "comment": "案件主管审核通过"})
        assert case["status"] == "新案待分配" and case["data"]["case_creation_approval_status"] == "已通过"
        fixed_tasks = call("GET", f"/cases/{case['id']}/tasks")["items"]
        assert {item["data"]["fixed_task_key"] for item in fixed_tasks if item["data"].get("task_type") == "固定任务"} == {"filing-registration", "service-tracking"}
        assert judicial["description"] == "刑事案件案情说明" and judicial["data"]["first_court_enabled"] is True
        call("PUT", f"/cases/{case['id']}/litigants", {"defendants": ["完成后禁止回退"]}, expected=(409,))
        call("PUT", f"/cases/{case['id']}/judicial", {"court": "完成后禁止重复完成"}, expected=(409,))
        call("PATCH", f"/records/{case['id']}", {"status": "已归档"}, expected=(409,))
        call("POST", f"/records/{case['id']}/transition", {"to_status": "文书准备", "comment": "禁止通用流转绕过"}, expected=(409,))
        call("DELETE", f"/records/{case['id']}", expected=(409,))
        creation_actions = {item["action"] for item in call("GET", f"/records/{case['id']}/history")["items"]}
        assert {"从合同新建案件", "维护当事人信息", "完成司法机关信息", "案件创建审批通过"}.issubset(creation_actions)
        admin_payload = {**case_payload, "serial_no": serial("ADMIN-CASE"), "title": "冒烟行政案件", "case_type": "行政案件及国家赔偿", "client_position": "原告/申请人", "cause_or_charge": "行政处罚撤销", "right_type": "行政诉讼"}
        call("POST", "/cases", {**admin_payload, "client_position": "被告人/犯罪嫌疑人"}, expected=(422,))
        admin_case = call("POST", "/cases", admin_payload, expected=(201,))
        records.append(admin_case["id"])
        assert admin_case["data"]["case_type"] == "行政案件及国家赔偿" and admin_case["data"]["right_type"] == "行政诉讼"
        admin_litigants = call("PUT", f"/cases/{admin_case['id']}/litigants", {
            "plaintiffs": ["冒烟行政原告"], "plaintiff_agents": ["行政代理人甲"],
            "defendants": ["冒烟行政机关"], "defendant_agents": ["行政机关代理人甲"],
            "third_parties": ["行政第三人"], "third_party_agents": [],
            "comment": "行政案件当事人阶段",
        })
        assert admin_litigants["data"]["case_creation_step"] == "litigants" and admin_litigants["data"]["plaintiffs"] == ["冒烟行政原告"]
        call("PUT", f"/cases/{admin_case['id']}/judicial", {}, expected=(422,))
        call("PUT", f"/cases/{admin_case['id']}/judicial", {"first_court_enabled": True, "first_court_name": "上海市行政测试人民法院", "public_security_name": "不应填写公安"}, expected=(422,))
        admin_judicial = call("PUT", f"/cases/{admin_case['id']}/judicial", {
            "first_court_enabled": True,
            "first_court_name": "上海市行政测试人民法院",
            "first_court_case_no": serial("ADMIN-JUDICIAL-NO"),
            "first_court_judge": "行政测试法官",
            "judicial_remark": "行政司法机关阶段验收",
        })
        assert admin_judicial["data"]["case_creation_step"] == "completed" and admin_judicial["data"]["first_court_name"] == "上海市行政测试人民法院"
        counsel_payload = {
            **case_payload,
            "serial_no": serial("COUNSEL-CASE"),
            "title": "冒烟法律顾问案件",
            "case_type": "法律顾问",
            "client_position": "不应保存的诉讼地位",
            "cause_or_charge": "不应保存的案由",
            "right_type": "不应保存的权利类型",
            "counsel_type": "常年法律顾问",
            "counsel_start": str(date.today()),
            "counsel_end": str(date.today() + timedelta(days=365)),
        }
        call("POST", "/cases", {**counsel_payload, "counsel_type": ""}, expected=(422,))
        call("POST", "/cases", {**counsel_payload, "counsel_start": None}, expected=(422,))
        call("POST", "/cases", {**counsel_payload, "counsel_end": str(date.today() - timedelta(days=1))}, expected=(422,))
        call("POST", "/cases", {**case_payload, "counsel_type": "越界顾问类型"}, expected=(422,))
        counsel_case = call("POST", "/cases", counsel_payload, expected=(201,))
        records.append(counsel_case["id"])
        assert counsel_case["data"]["case_type"] == "法律顾问"
        assert counsel_case["data"]["counsel_type"] == "常年法律顾问"
        assert counsel_case["data"]["counsel_start"] == str(date.today())
        assert counsel_case["data"]["counsel_end"] == str(date.today() + timedelta(days=365))
        assert counsel_case["data"]["cause_or_charge"] == "" and counsel_case["data"]["client_position"] == "" and counsel_case["data"]["right_type"] == ""
        call("PUT", f"/cases/{counsel_case['id']}/complete-creation", {}, expected=(409,))
        counsel_litigants = call("PUT", f"/cases/{counsel_case['id']}/litigants", {})
        assert counsel_litigants["data"]["case_creation_step"] == "litigants"
        call("PUT", f"/cases/{counsel_case['id']}/judicial", {}, expected=(409,))
        completed_counsel = call("PUT", f"/cases/{counsel_case['id']}/complete-creation", {"comment": "法律顾问两步流程完成"})
        assert completed_counsel["data"]["case_creation_step"] == "completed" and completed_counsel["status"] == "待立案审批"
        completed_counsel = call("POST", f"/cases/{counsel_case['id']}/creation/review", {"approved": True, "comment": "法律顾问立案审批通过"})
        call("PUT", f"/cases/{counsel_case['id']}/complete-creation", {}, expected=(409,))
        counsel_edit_payload = {
            "title": "冒烟法律顾问案件（已修改）",
            "counsel_type": "专项法律顾问",
            "counsel_start": str(date.today() + timedelta(days=1)),
            "counsel_end": str(date.today() + timedelta(days=180)),
            "handling_lawyers": [USERNAME],
            "assistant": USERNAME,
            "comment": "验证旧站基本信息修改闭环",
        }
        call("PUT", f"/cases/{counsel_case['id']}/counsel-basic", {**counsel_edit_payload, "counsel_end": str(date.today())}, expected=(422,))
        call("PUT", f"/cases/{case['id']}/counsel-basic", counsel_edit_payload, expected=(409,))
        edited_counsel = call("PUT", f"/cases/{counsel_case['id']}/counsel-basic", counsel_edit_payload)
        assert edited_counsel["title"] == "冒烟法律顾问案件（已修改）"
        assert edited_counsel["data"]["counsel_type"] == "专项法律顾问" and edited_counsel["data"]["assistant"] == USERNAME
        assert edited_counsel["data"]["counsel_start"] == str(date.today() + timedelta(days=1)) and edited_counsel["data"]["counsel_end"] == str(date.today() + timedelta(days=180))
        counsel_case_b = call("POST", "/cases", {
            **counsel_payload,
            "serial_no": serial("COUNSEL-CASE-B"),
            "title": "冒烟法律顾问案件 B",
            "counsel_type": "常年法律顾问",
            "counsel_start": str(date.today() - timedelta(days=30)),
            "counsel_end": str(date.today() + timedelta(days=335)),
        }, expected=(201,))
        records.append(counsel_case_b["id"])
        call("PUT", f"/cases/{counsel_case_b['id']}/litigants", {})
        call("PUT", f"/cases/{counsel_case_b['id']}/complete-creation", {"comment": "分页查询第二条法律顾问案件"})
        call("POST", f"/cases/{counsel_case_b['id']}/creation/review", {"approved": True, "comment": "第二条法律顾问立案审批通过"})
        counsel_capabilities = call("GET", f"/cases/{counsel_case['id']}/action-capabilities")
        assert all(counsel_capabilities[key] is True for key in ["can_upload_attachment", "can_delete_attachment", "can_create_reminder", "can_delete_reminder", "can_create_log"])
        counsel_attachment = multipart_upload("/attachments", {"record_id": counsel_case["id"], "category": "案件文件", "remark": "法律顾问文档筛选"}, f"counsel-filter-{suffix}.txt", b"counsel document")
        attachments.append(counsel_attachment["id"])
        counsel_search = {
            "scope": "company", "keyword": "冒烟法律顾问案件", "page": 1, "page_size": 1,
            "sort_order": "case_no_asc",
        }
        call("POST", "/cases/counsel/search", {**counsel_search, "scope": "invalid"}, expected=(422,))
        call("POST", "/cases/counsel/search", {**counsel_search, "sort_order": "invalid"}, expected=(422,))
        counsel_page_one = call("POST", "/cases/counsel/search", counsel_search)
        counsel_page_two = call("POST", "/cases/counsel/search", {**counsel_search, "page": 2})
        assert counsel_page_one["total"] == 2 and len(counsel_page_one["items"]) == 1
        assert len(counsel_page_two["items"]) == 1 and counsel_page_one["items"][0]["id"] != counsel_page_two["items"][0]["id"]
        assert counsel_page_one["items"][0]["serial_no"] < counsel_page_two["items"][0]["serial_no"]
        assert call("POST", "/cases/counsel/search", {**counsel_search, "document_name": f"counsel-filter-{suffix}.txt", "page_size": 10})["total"] == 1
        assert call("POST", "/cases/counsel/search", {**counsel_search, "counsel_type": "专项法律顾问", "page_size": 10})["total"] == 1
        assert call("POST", "/cases/counsel/search", {**counsel_search, "counsel_start": str(date.today() + timedelta(days=300)), "page_size": 10})["total"] == 1
        selected_export = call("POST", "/cases/counsel/export", {**counsel_search, "selected_only": True, "selected_ids": [counsel_case["id"]]}, raw=True)
        assert selected_export[0] == 200 and selected_export[2].startswith("text/csv") and selected_export[1].startswith(b"\xef\xbb\xbf")
        assert edited_counsel["serial_no"].encode() in selected_export[1] and counsel_case_b["serial_no"].encode() not in selected_export[1]
        all_counsel_export = call("POST", "/cases/counsel/export", {**counsel_search, "page_size": 200}, raw=True)
        assert edited_counsel["serial_no"].encode() in all_counsel_export[1] and counsel_case_b["serial_no"].encode() in all_counsel_export[1]
        call("POST", "/cases/counsel/export", {**counsel_search, "selected_only": True, "selected_ids": []}, expected=(422,))
        call("POST", "/cases/counsel/export", {**counsel_search, "selected_only": True, "selected_ids": [counsel_case["id"], case["id"]]}, expected=(403,))
        call("POST", f"/cases/{counsel_case['id']}/reminders", {
            "reminder_date": str(date.today() + timedelta(days=5)),
            "deadline": str(date.today() + timedelta(days=4)),
            "content": "错误的提醒日期顺序",
        }, expected=(422,))
        reminder = call("POST", f"/cases/{counsel_case['id']}/reminders", {
            "reminder_date": str(date.today() + timedelta(days=4)),
            "deadline": str(date.today() + timedelta(days=5)),
            "content": "冒烟法律顾问材料复核提醒",
        }, expected=(201,))
        reminder_list = call("GET", f"/cases/{counsel_case['id']}/reminders")
        assert reminder_list["total"] == 1 and reminder_list["items"][0]["id"] == reminder["id"]
        call("POST", "/records", {"module": "case_reminder", "serial_no": serial("BYPASS-REMINDER"), "title": "绕过提醒"}, expected=(422,))
        call("PATCH", f"/records/{reminder['id']}", {"title": "绕过修改提醒"}, expected=(409,))
        call("POST", f"/records/{reminder['id']}/transition", {"to_status": "失效", "comment": "绕过提醒状态"}, expected=(409,))
        call("DELETE", f"/records/{reminder['id']}", expected=(409,))
        call("DELETE", f"/cases/{counsel_case['id']}/reminders/{reminder['id']}", expected=(204,))
        assert call("GET", f"/cases/{counsel_case['id']}/reminders")["total"] == 0
        case_log = call("POST", f"/cases/{counsel_case['id']}/logs", {"content": "冒烟法律顾问案件日志"}, expected=(201,))
        assert case_log["content"] == "冒烟法律顾问案件日志"
        assert call("GET", f"/cases/{counsel_case['id']}/logs")["items"][0]["id"] == case_log["id"]
        batch_updated = call("POST", "/cases/batch-update", {
            "case_ids": [counsel_case["id"], counsel_case_b["id"]],
            "handling_lawyers": [USERNAME], "assistant": USERNAME,
            "case_stage": "顾问服务中", "comment": "法律顾问批量修改验收",
        })
        assert batch_updated["updated"] == 2 and all(item["data"]["case_stage"] == "顾问服务中" for item in batch_updated["items"])
        call("POST", "/cases/batch-fees", {
            "case_ids": [counsel_case["id"]], "amount": 100,
            "expense_scope": "内部", "expense_subtype": "官费", "handler": USERNAME,
        }, expected=(422,))
        call("POST", "/cases/batch-fees", {
            "case_ids": [counsel_case["id"], 999999999], "amount": 100,
            "expense_scope": "律所", "expense_subtype": "官费", "handler": USERNAME,
        }, expected=(404,))
        batch_fees = call("POST", "/cases/batch-fees", {
            "case_ids": [counsel_case["id"], counsel_case_b["id"]], "amount": 188.50,
            "expense_scope": "律所", "expense_subtype": "官费", "handler": USERNAME,
            "description": "法律顾问批量费用验收",
        }, expected=(201,))
        assert batch_fees["created"] == 2 and all(item["data"]["amount"] == 188.5 for item in batch_fees["items"])
        records.extend(item["id"] for item in batch_fees["items"])
        counsel_attachment_b = multipart_upload("/attachments", {"record_id": counsel_case["id"], "category": "案件文件", "remark": "法律顾问批量文件验收"}, f"counsel-batch-{suffix}.txt", b"second counsel document")
        attachments.append(counsel_attachment_b["id"])
        zip_status, zip_payload, zip_type = call("POST", "/cases/attachments/download", {"attachment_ids": [counsel_attachment["id"], counsel_attachment_b["id"]]}, raw=True)
        assert zip_status == 200 and zip_type.startswith("application/zip")
        with zipfile.ZipFile(io.BytesIO(zip_payload)) as archive:
            assert {f"counsel-filter-{suffix}.txt", f"counsel-batch-{suffix}.txt"}.issubset(set(archive.namelist()))
        call("POST", "/cases/attachments/delete", {"attachment_ids": [counsel_attachment["id"], 999999999]}, expected=(404,))
        deleted_files = call("POST", "/cases/attachments/delete", {"attachment_ids": [counsel_attachment["id"], counsel_attachment_b["id"]]})
        assert deleted_files["deleted"] == 2
        attachments.remove(counsel_attachment["id"]); attachments.remove(counsel_attachment_b["id"])
        assert call("GET", f"/attachments?record_id={counsel_case['id']}")["total"] == 0
        counsel_actions = {item["action"] for item in call("GET", f"/records/{counsel_case['id']}/history")["items"]}
        assert {"从合同新建案件", "维护当事人信息", "完成法律顾问案件新建", "修改法律顾问案件基本信息", "新增案件提醒", "删除案件提醒", "新增案件日志", "批量修改案件", "批量新增案件费用", "批量删除案件文件"}.issubset(counsel_actions)
        assigned = call("POST", f"/cases/{case['id']}/assign", assignment_payload)
        assert assigned["status"] == "文书准备"
        first_instance = call("POST", f"/cases/{case['id']}/progress", {"first_instance_court": "上海市测试人民法院", "first_instance_case_no": serial("FIRST-COURT-NO"), "judge": "测试法官", "clerk": "测试书记员", "comment": "一审立案"})
        assert first_instance["status"] == "一审立案受理"
        hearing = call("POST", "/hearings", {"case_record_id": case["id"], "hearing_date": str(date.today() + timedelta(days=20)), "hearing_time": "09:30:00", "court": "上海市测试人民法院", "hearing_lawyer": USERNAME}, expected=(201,))
        hearings.append(hearing["id"])
        assert call("GET", f"/records/{case['id']}")["status"] == "一审准备开庭"
        assert call("GET", "/hearings")["total"] >= 1
        call("DELETE", f"/hearings/{hearing['id']}", expected=(204,)); hearings.remove(hearing["id"])
        judgment = call("POST", f"/cases/{case['id']}/progress", {"judgment_date": str(date.today()), "judgment_document_no": serial("JUDGMENT"), "comment": "收到一审裁判文书"})
        assert judgment["status"] == "待上诉"
        second_instance = call("POST", f"/cases/{case['id']}/progress", {"second_instance_court": "上海市第二中级人民法院", "second_instance_case_no": serial("SECOND-COURT-NO"), "comment": "二审受理"})
        assert second_instance["status"] == "二审"
        archive_case = call("POST", "/cases", {"contract_record_id": contract["id"], "serial_no": serial("ARCHIVE-CASE"), "title": "归档审核冒烟案件", "status": "新案待分配", "owner": USERNAME, "case_type": "刑事案件", "client_position": "被告人/犯罪嫌疑人", "cause_or_charge": "归档测试罪名", "handling_lawyers": [USERNAME]}, expected=(201,))
        records.append(archive_case["id"])
        call("PUT", f"/cases/{archive_case['id']}/litigants", {})
        archive_case = call("PUT", f"/cases/{archive_case['id']}/judicial", {"court": "上海市测试人民法院"})
        archive_case = call("POST", f"/cases/{archive_case['id']}/creation/review", {"approved": True, "comment": "归档测试案件立案审批通过"})
        for fixed_task in call("GET", f"/cases/{archive_case['id']}/tasks")["items"]:
            call("POST", f"/tasks/{fixed_task['id']}/accept", {"comment": "归档前办理固定任务"})
            call("POST", f"/tasks/{fixed_task['id']}/complete", {"comment": "固定任务成果已提交"})
            call("POST", f"/tasks/{fixed_task['id']}/confirm", {"comment": "案件主管验收通过"})
        archive_payload = {"case_closed": True, "fees_settled": True, "documents_complete": True, "finance_complete": True, "archive_no": serial("ARCHIVE-NO"), "paper_archive_location": "测试档案室 A-01", "paper_volume_count": 2, "comment": "提交归档审核", "submit": True}
        call("POST", f"/cases/{archive_case['id']}/archive", archive_payload, expected=(409,))
        closed_archive_case = call("POST", f"/cases/{archive_case['id']}/close", {"comment": "案件实体流程已办结"})
        assert closed_archive_case["data"]["case_closed_at"] and closed_archive_case["data"]["case_closed_by"] == USERNAME
        for category in ["委托材料", "证据材料", "诉讼文书", "裁判文书"]:
            archive_file = multipart_upload("/attachments", {"record_id": archive_case["id"], "category": category, "remark": "归档真实条件验收"}, f"smoke-archive-{category}-{suffix}.txt", category.encode("utf-8"))
            attachments.append(archive_file["id"])
        pending_archive = call("POST", f"/cases/{archive_case['id']}/archive", archive_payload)
        assert pending_archive["record"]["status"] == "待归档审核"
        archived_capabilities = call("GET", f"/cases/{archive_case['id']}/action-capabilities")
        assert all(archived_capabilities[key] is False for key in ["can_upload_attachment", "can_delete_attachment", "can_create_reminder", "can_delete_reminder", "can_create_log"])
        call("POST", f"/cases/{archive_case['id']}/logs", {"content": "归档中案件不得新增日志"}, expected=(409,))
        multipart_upload("/attachments", {"record_id": archive_case["id"], "category": "案件文档", "remark": "归档中案件不得上传"}, f"archive-write-denied-{suffix}.txt", b"denied", expected=(409,))
        rejected_archive = call("POST", f"/cases/{archive_case['id']}/archive/review", {"approved": False, "comment": "缺少纸质签收页，请补齐"})
        assert rejected_archive["status"] == "一审准备开庭" and rejected_archive["data"]["archive_reject_reason"]
        pending_archive = call("POST", f"/cases/{archive_case['id']}/archive", archive_payload)
        approved_archive = call("POST", f"/cases/{archive_case['id']}/archive/review", {"approved": True, "comment": "归档材料审核通过"})
        assert approved_archive["status"] == "已归档" and approved_archive["data"]["archive_no"] == archive_payload["archive_no"]
        requested_unarchive = call("POST", f"/cases/{archive_case['id']}/unarchive/request", {"reason": "归档后发现裁判文书编号需要依法更正"})
        assert requested_unarchive["data"]["unarchive_request"]["status"] == "待审批"
        unarchived = call("POST", f"/cases/{archive_case['id']}/unarchive/review", {"approved": True, "comment": "特殊审批同意解档"})
        assert unarchived["status"] != "已归档" and unarchived["data"]["unarchive_request"]["status"] == "已通过"
        passed("案件关联合同、手工立案审批、固定任务、人员分配、诉讼要素自动推进阶段、开庭、两级归档及特殊解档审批")

        call("POST", "/records", {"module": "clue", "serial_no": serial("BYPASS-CLUE"), "title": f"SMOKE禁止通用线索-{suffix}", "status": "草稿", "owner": USERNAME, "department": "上海分所", "customer": "冒烟测试客户", "data": {"platform": "淘宝", "product": "测试侵权商品"}}, expected=(422,))
        smoke_investigation = call("POST", "/investigations/records", {"module": "investigation", "serial_no": serial("SMOKE-INV"), "title": f"SMOKE线索来源调查-{suffix}", "status": "待分配", "owner": USERNAME, "department": "上海分所", "customer": "冒烟测试客户", "data": {"authorized_from": str(date.today()), "authorized_to": str(date.today() + timedelta(days=30)), "region": "上海", "right_type": "商标", "customer_review": True}}, expected=(201,))
        records.append(smoke_investigation["id"])
        smoke_task = call("POST", f"/investigations/{smoke_investigation['id']}/tasks", {"title": f"SMOKE线索取证任务-{suffix}", "owner": USERNAME, "deadline": str(date.today() + timedelta(days=6)), "priority": "普通", "description": "线索创建来源任务"}, expected=(201,))
        records.append(smoke_task["id"])
        clue = call("POST", "/investigations/records", {"module": "clue", "serial_no": serial("SMOKE-CLUE"), "title": f"SMOKE调查线索-{suffix}", "status": "草稿", "owner": USERNAME, "department": "上海分所", "customer": "冒烟测试客户", "data": {"platform": "淘宝", "product": "测试侵权商品", "source_task_id": smoke_task["id"], "customer_review": False}}, expected=(201,))
        records.append(clue["id"])
        assert clue["status"] == "草稿" and clue["data"]["source_task_id"] == smoke_task["id"] and clue["data"]["customer_review"] is True
        call("POST", f"/records/{clue['id']}/transition", {"to_status": "调查中", "comment": "禁止绕过审批"}, expected=(409,))
        call("PATCH", f"/records/{clue['id']}", {"title": "不应通过通用入口修改"}, expected=(409,))
        draft_edited_clue = call("PATCH", f"/investigations/records/{clue['id']}", {"title": f"SMOKE调查线索已补材料-{suffix}", "data": {"platform": "淘宝", "product": "测试侵权商品", "region": "上海"}})
        assert draft_edited_clue["title"].endswith(suffix) and draft_edited_clue["data"]["region"] == "上海"
        submitted_clue = call("POST", f"/investigations/clues/{clue['id']}/submit", {"comment": "提交调查线索审批"})
        assert submitted_clue["status"] == "待审批"
        rejected_clue = call("POST", f"/investigations/clues/{clue['id']}/review", {"approved": False, "comment": "请补充调查区域后重新提交"})
        assert rejected_clue["status"] == "已驳回"
        retried_clue = call("PATCH", f"/investigations/records/{clue['id']}", {"title": f"SMOKE调查线索驳回后重提-{suffix}", "data": {"region": "上海浦东新区"}})
        assert retried_clue["title"].endswith(suffix) and retried_clue["status"] == "已驳回" and retried_clue["data"]["region"] == "上海浦东新区"
        resubmitted_clue = call("POST", f"/investigations/clues/{clue['id']}/submit", {"comment": "补充调查区域后重新提交审批"})
        assert resubmitted_clue["status"] == "待审批"
        approved_after_retry = call("POST", f"/investigations/clues/{clue['id']}/review", {"approved": True, "comment": "补正后内部审批通过"})
        assert approved_after_retry["status"] == "待客户审核"
        call("PATCH", f"/investigations/records/{clue['id']}", {"title": "待客户审核不可直接修改"}, expected=(409,))
        customer_approved = call("POST", f"/investigations/clues/{clue['id']}/customer-review", {"approved": True, "comment": "客户确认后进入取证"})
        assert customer_approved["status"] == "待取证" and customer_approved["data"]["customer_reviewer"] == USERNAME
        premature_cases = call("POST", "/investigations/clues/batch-cases", {"clue_ids": [clue["id"]], "contract_record_id": contract["id"]}, expected=(201,))
        assert premature_cases["created"] == 0 and premature_cases["failed"] == 1
        collected_clue = call("POST", f"/investigations/clues/{clue['id']}/collect", {"collected_at": str(date.today()), "notary_institution": "上海市测试公证处", "comment": "当日完成取证"})
        assert collected_clue["status"] == "已取证" and collected_clue["data"]["notary_institution"] == "上海市测试公证处"
        assigned_clue = call("POST", f"/investigations/{clue['id']}/assign", {"investigator": USERNAME, "comment": "调查员分配验收"})
        assert assigned_clue["owner"] == USERNAME and assigned_clue["data"]["assigned_by"] == USERNAME
        fee_application = call("POST", f"/investigations/clues/{clue['id']}/fee-application", {"amount": 88.5, "fee_type": "调查交通费", "description": "调查费用申请验收"}, expected=(201,))
        records.append(fee_application["fee"]["id"])
        assert fee_application["fee"]["module"] == "finance" and fee_application["clue"]["data"]["fee_application_id"] == fee_application["fee"]["id"]
        call("POST", f"/investigations/clues/{clue['id']}/fee-application", {"amount": 1, "fee_type": "重复申请"}, expected=(409,))

        evidence = call("POST", f"/investigations/clues/{clue['id']}/evidence", {"title": f"SMOKE证据目录-{suffix}", "owner": USERNAME, "source": "平台网页取证", "description": "调查证据闭环验收"}, expected=(201,))
        records.append(evidence["id"])
        parent_task = call("POST", f"/investigations/{clue['id']}/tasks", {"title": "调查取证主任务", "owner": USERNAME, "deadline": str(date.today() + timedelta(days=6)), "priority": "紧急", "description": "主任务"}, expected=(201,))
        records.append(parent_task["id"])
        child_task = call("POST", f"/investigations/{clue['id']}/tasks", {"title": "平台截图子任务", "owner": USERNAME, "deadline": str(date.today() + timedelta(days=3)), "priority": "普通", "parent_task_id": parent_task["id"], "description": "子任务"}, expected=(201,))
        records.append(child_task["id"])
        assert child_task["parent_task_id"] == parent_task["id"] and child_task["parent_task_no"] == parent_task["serial_no"]
        reassigned_task = call("POST", f"/investigations/{child_task['id']}/assign", {"investigator": USERNAME, "comment": "子任务调查员验收"})
        assert reassigned_task["owner"] == USERNAME
        deletable_task = call("POST", f"/investigations/{clue['id']}/tasks", {"title": "待删除调查子任务", "owner": manager_name, "deadline": str(date.today() + timedelta(days=2)), "priority": "普通", "description": "批量删除验收"}, expected=(201,))
        records.append(deletable_task["id"])
        local_db_scalar(f"SELECT count(*) FROM notifications WHERE source_type='task' AND source_id={int(deletable_task['id'])};", label="调查任务删除前通知")
        deleted_investigation = call("POST", "/investigations/batch-delete", {"record_ids": [deletable_task["id"]], "comment": "删除未开始调查任务"})
        assert deleted_investigation["failed"] == 0
        call("GET", f"/records/{deletable_task['id']}", expected=(404,))
        assert local_db_scalar(f"SELECT count(*) FROM notifications WHERE source_type='task' AND source_id={int(deletable_task['id'])};", label="调查任务删除后通知") == 0
        records.remove(deletable_task["id"])
        investigation_tasks = call("GET", f"/investigations/{clue['id']}/tasks")
        assert investigation_tasks["total"] == 2
        evidence_catalog = multipart_upload("/attachments", {"record_id": evidence["id"], "category": "证据目录", "remark": "证据目录验收"}, "evidence-catalog.txt", b"evidence catalog")
        evidence_scan = multipart_upload("/attachments", {"record_id": evidence["id"], "category": "证据扫描件", "remark": "证据扫描件验收"}, "evidence-scan.txt", b"evidence scan")
        attachments.extend([evidence_catalog["id"], evidence_scan["id"]])
        organized = call("POST", f"/investigations/evidence/{evidence['id']}/organize", {"comment": "证据整理完成"})
        assert organized["status"] == "已整理"
        filed = call("POST", f"/investigations/evidence/{evidence['id']}/file", {"comment": "证据材料入卷"})
        assert filed["status"] == "已入卷"
        due = date.today() + timedelta(days=20)
        csv_content = (f"来源线索编号,公证标题,负责人,审核截止日,说明\r\n{clue['serial_no']},SMOKE公证审核-{suffix},{USERNAME},{due},批量导入测试\r\n{clue['serial_no']},重复公证,{USERNAME},{due},应被拦截\r\n").encode("utf-8-sig")
        imported = multipart_upload("/investigations/notaries/import", {}, "smoke-notaries.csv", csv_content)
        assert imported["created"] == 1 and imported["failed"] == 1 and imported["errors"][0]["error"]
        records.extend(imported["created_ids"])
        imported_notary = call("GET", f"/records/{imported['created_ids'][0]}")
        call("PATCH", f"/records/{imported_notary['id']}", {"status": "审核通过"}, expected=(409,))
        call("POST", f"/records/{imported_notary['id']}/transition", {"to_status": "审核通过", "comment": "绕过公证审核"}, expected=(409,))
        call("DELETE", f"/records/{imported_notary['id']}", expected=(409,))
        updated_clue = call("GET", f"/records/{clue['id']}")
        assert imported_notary["status"] == "等待材料" and imported_notary["data"]["clue_no"] == clue["serial_no"] and updated_clue["data"]["notary_record_id"] == imported_notary["id"]
        imported_certificate_no = serial("NOTARY-CERT")
        imported_invoice_no = serial("NOTARY-INV")
        storage_csv = (f"clue_no,certificate_no,warehouse,invoice_no,case_no,investigator\r\n{clue['serial_no']},{imported_certificate_no},测试公证仓库 A-01,{imported_invoice_no},{case['serial_no']},{USERNAME}\r\n").encode("utf-8-sig")
        storage_import = multipart_upload("/investigations/notaries/storage/import", {}, "smoke-notary-storage.csv", storage_csv)
        assert storage_import["updated"] == 1 and storage_import["failed"] == 0 and storage_import["items"][0]["公证书号"] == imported_certificate_no and storage_import["items"][0]["仓库"] == "测试公证仓库 A-01"
        stored_notary = call("GET", f"/records/{imported_notary['id']}")
        assert stored_notary["data"]["certificate_no"] == imported_certificate_no and stored_notary["data"]["invoice_no"] == imported_invoice_no and stored_notary["data"]["warehouse"] == "测试公证仓库 A-01"
        multipart_upload("/investigations/notaries/files/import", {}, "smoke-missing-certificate.pdf", b"%PDF-1.4\n%%EOF", expected=(422,))
        multipart_upload("/investigations/notaries/invoices/import", {}, "smoke-missing-invoice.pdf", b"%PDF-1.4\n%%EOF", expected=(422,))
        certificate_import = multipart_upload("/investigations/notaries/files/import", {"certificate_no": imported_certificate_no}, "smoke-certificate.pdf", b"%PDF-1.4\nsmoke certificate\n%%EOF")
        invoice_import = multipart_upload("/investigations/notaries/invoices/import", {"invoice_no": imported_invoice_no}, "smoke-invoice.pdf", b"%PDF-1.4\nsmoke invoice\n%%EOF")
        attachments.extend([certificate_import["attachment"]["id"], invoice_import["attachment"]["id"]])
        assert certificate_import["record_id"] == imported_notary["id"] and certificate_import["attachment"]["category"] == "公证书扫描件"
        assert invoice_import["record_id"] == imported_notary["id"] and invoice_import["attachment"]["category"] == "公证发票"
        multipart_upload("/investigations/notaries/files/import", {"certificate_no": serial("NOTARY-MISSING")}, "smoke-unmatched-certificate.pdf", b"%PDF-1.4\n%%EOF", expected=(422,))
        batch_cases = call("POST", "/investigations/clues/batch-cases", {"clue_ids": [clue["id"]], "contract_record_id": contract["id"], "case_type": "民事案件", "court": "上海市测试人民法院"}, expected=(201,))
        assert batch_cases["created"] == 1 and batch_cases["failed"] == 0
        records.extend(batch_cases["created_ids"])
        batch_case = call("GET", f"/records/{batch_cases['created_ids'][0]}")
        assert batch_case["status"] == "等待公证书" and batch_case["data"]["contract_id"] == contract["id"] and batch_case["data"]["clue_id"] == clue["id"]
        certificate = call("POST", f"/notaries/{imported_notary['id']}/certificate", {"certificate_no": imported_certificate_no, "issued_date": str(date.today()), "storage_location": "测试档案室 GZ-01", "physical_received": True, "comment": "公证书登记验收"})
        assert certificate["data"]["physical_received"] is True and certificate["data"]["certificate_storage_location"] == "测试档案室 GZ-01"
        notary_scan = multipart_upload("/attachments", {"record_id": imported_notary["id"], "category": "公证书扫描件", "remark": "公证书及发票合并扫描件"}, "notary-scan.txt", b"notary and invoice scan")
        attachments.append(notary_scan["id"])
        pending_notary = call("GET", f"/records/{imported_notary['id']}")
        pending_case = call("GET", f"/records/{batch_case['id']}")
        assert pending_notary["status"] == "待审核" and pending_notary["data"]["review_due_date"] and pending_case["status"] == "等待审核公证书"
        reviewed_notary = call("POST", f"/notaries/{imported_notary['id']}/review", {"approved": True, "comment": "公证主要信息核对无误", "case_type": "民事案件", "court": "上海市测试人民法院"})
        assert reviewed_notary["case"]["id"] == batch_case["id"] and reviewed_notary["case"]["status"] == "新案待分配"
        assigned_notary_case = call("POST", f"/cases/{batch_case['id']}/assign", {"customer_manager": USERNAME, "hearing_lawyer": USERNAME, "handling_lawyers": [USERNAME], "assistant": USERNAME, "comment": "分配后触发原件交接"})
        handoff_task_id = assigned_notary_case["data"]["notary_handoff_task_id"]
        records.append(handoff_task_id)
        handoff_task = call("GET", f"/records/{handoff_task_id}")
        assert handoff_task["status"] == "待接收" and handoff_task["data"]["auto_task_type"] == "notary_original_handoff" and handoff_task["data"]["case_no"] == batch_case["serial_no"]
        case_task_items = call("GET", f"/cases/{batch_case['id']}/tasks")
        assert handoff_task_id in {item["id"] for item in case_task_items["items"]}
        call("POST", f"/tasks/{handoff_task_id}/accept", {"comment": "扫描文员接收交接任务"})
        submitted_handoff = call("POST", f"/tasks/{handoff_task_id}/complete", {"comment": "原件已交给案件文书人员"})
        assert submitted_handoff["status"] == "已完成" and submitted_handoff["workflow_status"] == "已完成" and submitted_handoff["completion_auto_confirm_at"]
        restarted_handoff = call("POST", f"/tasks/{handoff_task_id}/restart", {"comment": "文书反馈尚未收到原件，重启任务"})
        assert restarted_handoff["status"] == "处理中"
        call("POST", f"/tasks/{handoff_task_id}/complete", {"comment": "重新交接完成"})
        call("POST", f"/tasks/{handoff_task_id}/confirm", {"comment": "确认收到公证书及发票原件"})
        call("POST", "/cases/batch-update", {"case_ids": [batch_case["id"]]}, expected=(422,))
        call("POST", "/cases/batch-update", {"case_ids": [], "case_nos": [], "assistant": USERNAME}, expected=(422,))
        unknown_case_nos = [serial("MISSING-CASE-A"), serial("MISSING-CASE-B")]
        missing_case_result = call("POST", "/cases/batch-update", {"case_nos": unknown_case_nos, "assistant": USERNAME}, expected=(404,))
        assert all(case_no in missing_case_result["detail"] for case_no in unknown_case_nos)
        batch_modified_by_no = call("POST", "/cases/batch-update", {"case_nos": [batch_case["serial_no"], batch_case["serial_no"]], "assistant": USERNAME, "comment": "按案号批量修改验收"})
        assert batch_modified_by_no["updated"] == 1 and batch_modified_by_no["items"][0]["data"]["assistant"] == USERNAME
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            call("POST", "/cases/batch-update", {"case_nos": [batch_case["serial_no"]], "assistant": manager_name}, expected=(404,))
        finally:
            TOKEN = admin_token
        batch_modified_case = call("POST", "/cases/batch-update", {"case_ids": [batch_case["id"]], "hearing_lawyer": USERNAME, "handling_lawyers": [USERNAME, member_name], "assistant": USERNAME, "case_stage": "一审准备开庭", "comment": "待结算页批量修改案件验收"})
        assert batch_modified_case["updated"] == 1 and batch_modified_case["items"][0]["data"]["handling_lawyers"] == [USERNAME, member_name] and batch_modified_case["items"][0]["data"]["case_stage"] == "一审准备开庭"
        assert any(item["action"] == "批量修改案件" for item in call("GET", f"/records/{batch_case['id']}/history")["items"])
        duplicate_batch = call("POST", "/investigations/clues/batch-cases", {"clue_ids": [clue["id"]], "contract_record_id": contract["id"]}, expected=(201,))
        assert duplicate_batch["created"] == 0 and duplicate_batch["failed"] == 1
        passed("线索取证/调查员分配/费用申请/批量删除、公证四类导入、公证审核、等待公证书转案、分案后原件交接自动任务及案件批量修改")

        admin_token = TOKEN
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            outside_task = call("POST", "/tasks", {"title": "SMOKE外部门任务", "owner": manager_name, "deadline": str(date.today() + timedelta(days=8)), "priority": "普通", "source": "日常任务"}, expected=(201,))
            company_owned_lifecycle_task = call("POST", "/tasks", {"title": "SMOKE公司接受管理员生命周期", "owner": outsider_name, "deadline": str(date.today() + timedelta(days=8)), "priority": "普通", "source": "日常任务"}, expected=(201,))
            company_collab_admin_task = call("POST", "/tasks", {"title": "SMOKE公司协作管理员范围", "owner": outsider_name, "collaborators": [department_peer_name], "deadline": str(date.today() + timedelta(days=8)), "priority": "普通", "source": "日常任务"}, expected=(201,))
        finally:
            TOKEN = admin_token
        records.append(outside_task["id"])
        records.append(company_owned_lifecycle_task["id"])
        records.append(company_collab_admin_task["id"])
        department_collab_task = call("POST", "/tasks", {"title": "SMOKE部门协作范围任务", "owner": outsider_name, "collaborators": [department_peer_name], "deadline": str(date.today() + timedelta(days=8)), "priority": "普通", "source": "日常任务"}, expected=(201,))
        records.append(department_collab_task["id"])
        task_feedback_attachment = multipart_upload("/attachments", {"record_id": department_collab_task["id"], "category": "任务反馈附件", "remark": "任务反馈附件权限验收"}, f"task-feedback-{suffix}.txt", b"task feedback attachment")
        attachments.append(task_feedback_attachment["id"])
        task_feedback_query = urllib.parse.urlencode({"record_id": department_collab_task["id"], "category": "任务反馈附件"})
        assert any(item["id"] == task_feedback_attachment["id"] for item in call("GET", f"/attachments?{task_feedback_query}")["items"])
        assert call("GET", f"/attachments/{task_feedback_attachment['id']}/download", raw=True)[0] == 200
        multipart_upload("/attachments", {"record_id": department_collab_task["id"], "category": "普通附件", "remark": "任务附件分类不得绕过"}, f"task-feedback-category-{suffix}.txt", b"invalid category", expected=(422,))
        # 部门经理拥有部门列表读取权，但不能借部门身份替代真正负责人执行任务生命周期，
        # 也不能先通过调查分配/批量修改旁路把负责人改成自己再执行。
        peer_manager_token = login(peer_manager_name, "SmokePass2026!")["access_token"]
        try:
            TOKEN = peer_manager_token
            call("GET", "/tasks?scope=company&relation=initiated", expected=(403,))
            call("GET", "/tasks?scope=company&relation=owned", expected=(403,))
            call("GET", "/tasks?scope=company&relation=collaborating", expected=(403,))
            peer_owned_query = urllib.parse.urlencode({"scope": "department", "relation": "owned", "serial_no": outside_task["serial_no"], "page_size": 1})
            peer_owned_page = call("GET", f"/tasks?{peer_owned_query}")
            assert peer_owned_page["total"] == 1 and peer_owned_page["items"][0]["id"] == outside_task["id"]
            peer_collab_query = urllib.parse.urlencode({"scope": "department", "relation": "collaborating", "serial_no": department_collab_task["serial_no"], "page_size": 1})
            peer_collab_page = call("GET", f"/tasks?{peer_collab_query}")
            assert peer_collab_page["total"] == 1 and peer_collab_page["items"][0]["id"] == department_collab_task["id"]
            call("POST", f"/tasks/{outside_task['id']}/accept", {"comment": "旁观经理不得代接收"}, expected=(403,))
            call("POST", f"/tasks/{outside_task['id']}/reject", {"comment": "旁观经理不得代拒绝"}, expected=(403,))
            call("POST", f"/tasks/{outside_task['id']}/restart", {"comment": "旁观经理不得代重启"}, expected=(403,))
            call("POST", f"/tasks/{outside_task['id']}/complete", {"comment": "旁观经理不得代完成"}, expected=(403,))
            call("POST", f"/tasks/{outside_task['id']}/handoff", {"recipient": peer_manager_name, "comment": "旁观经理不得代交接"}, expected=(403,))
            call("POST", "/tasks/batch-update", {"task_ids": [outside_task["id"]], "owner": peer_manager_name, "comment": "部门权限不得替换负责人"}, expected=(403,))
            call("POST", f"/investigations/{outside_task['id']}/assign", {"investigator": peer_manager_name, "comment": "调查入口不得绕过任务负责人权限"}, expected=(403,))
            denied_delete = call("POST", "/investigations/batch-delete", {"record_ids": [outside_task["id"]]})
            assert denied_delete["deleted"] == 0 and denied_delete["failed"] == 1
            call("POST", f"/tasks/{department_collab_task['id']}/accept", {"comment": "旁观经理不得代接收部门协作任务"}, expected=(403,))
            call("POST", f"/tasks/{department_collab_task['id']}/reject", {"comment": "旁观经理不得代拒绝部门协作任务"}, expected=(403,))
            call("POST", f"/tasks/{department_collab_task['id']}/restart", {"comment": "旁观经理不得代重启部门协作任务"}, expected=(403,))
            call("POST", f"/tasks/{department_collab_task['id']}/complete", {"comment": "旁观经理不得代完成部门协作任务"}, expected=(403,))
            call("POST", f"/tasks/{department_collab_task['id']}/confirm", {"comment": "旁观经理不得代确认部门协作任务"}, expected=(403,))
            call("POST", f"/tasks/{department_collab_task['id']}/handoff", {"recipient": peer_manager_name, "comment": "旁观经理不得代交接部门协作任务"}, expected=(403,))
            call("POST", f"/tasks/{department_collab_task['id']}/comments", {"comment": "部门列表读取权不得冒充参与人"}, expected=(403,))
            call("GET", f"/tasks/{department_collab_task['id']}/history", expected=(403,))
            # A department observer may not discover task feedback attachment
            # existence.  The generic attachment gateway can therefore return
            # either an explicit participant denial or its standard no-access
            # 404 before the task-specific guard is reached.
            call("GET", f"/attachments?{task_feedback_query}", expected=(403, 404))
            call("GET", f"/attachments/{task_feedback_attachment['id']}/download", expected=(403, 404))
            multipart_upload("/attachments", {"record_id": department_collab_task["id"], "category": "任务反馈附件", "remark": "非参与人不得上传任务反馈"}, f"task-feedback-denied-{suffix}.txt", b"forbidden", expected=(403, 404))
            call("POST", "/tasks/batch-update", {"task_ids": [department_collab_task["id"]], "owner": peer_manager_name, "comment": "部门协作读取权不得替换负责人"}, expected=(403,))
            call("POST", f"/investigations/{department_collab_task['id']}/assign", {"investigator": peer_manager_name, "comment": "部门协作读取权不得绕过负责人权限"}, expected=(404,))
            call("PATCH", f"/records/{department_collab_task['id']}", {"owner": peer_manager_name}, expected=(404,))
            call("POST", f"/records/{department_collab_task['id']}/transition", {"to_status": "处理中", "comment": "部门协作读取权不得变更状态"}, expected=(404,))
            call("DELETE", f"/records/{department_collab_task['id']}", expected=(403,))
            denied_collab_delete = call("POST", "/investigations/batch-delete", {"record_ids": [department_collab_task["id"]]})
            assert denied_collab_delete["deleted"] == 0 and denied_collab_delete["failed"] == 1
        finally:
            TOKEN = admin_token
        unchanged_outside_task = call("GET", f"/records/{outside_task['id']}")
        assert unchanged_outside_task["owner"] == manager_name and unchanged_outside_task["status"] == "待接收"
        unchanged_department_collab_task = call("GET", f"/records/{department_collab_task['id']}")
        assert unchanged_department_collab_task["owner"] == outsider_name and unchanged_department_collab_task["status"] == "待接收"
        try:
            TOKEN = login(department_peer_name, "SmokePass2026!")["access_token"]
            department_peer_task = call("POST", "/tasks", {"title": "SMOKE同部门成员发起任务", "owner": outsider_name, "deadline": str(date.today() + timedelta(days=8)), "priority": "普通", "source": "日常任务"}, expected=(201,))
            call("GET", "/tasks?scope=department&relation=initiated", expected=(403,))
            call("GET", "/tasks?scope=department&relation=owned", expected=(403,))
            call("GET", "/tasks?scope=department&relation=collaborating", expected=(403,))
            call("GET", "/tasks?scope=company&relation=initiated", expected=(403,))
            call("GET", "/tasks?scope=company&relation=owned", expected=(403,))
            call("GET", "/tasks?scope=company&relation=collaborating", expected=(403,))
            assert company_collab_admin_task["initiator"] == manager_name and company_collab_admin_task["owner"] == outsider_name
            pure_company_comment = call("POST", f"/tasks/{company_collab_admin_task['id']}/comments", {"comment": "公司纯协作者只允许沟通"}, expected=(201,))
            assert any(item["id"] == pure_company_comment["id"] for item in call("GET", f"/tasks/{company_collab_admin_task['id']}/history")["items"])
            call("POST", f"/tasks/{company_collab_admin_task['id']}/accept", {"comment": "纯协作者不得接收"}, expected=(403,))
            call("POST", f"/tasks/{company_collab_admin_task['id']}/reject", {"comment": "纯协作者不得拒绝"}, expected=(403,))
            call("POST", f"/tasks/{company_collab_admin_task['id']}/restart", {"comment": "纯协作者不得重启"}, expected=(403,))
            call("POST", f"/tasks/{company_collab_admin_task['id']}/complete", {"comment": "纯协作者不得完成"}, expected=(403,))
            call("POST", f"/tasks/{company_collab_admin_task['id']}/confirm", {"comment": "纯协作者不得确认"}, expected=(403,))
            call("POST", f"/tasks/{company_collab_admin_task['id']}/handoff", {"recipient": department_peer_name, "comment": "纯协作者不得交接"}, expected=(403,))
            call("POST", "/tasks/batch-update", {"task_ids": [company_collab_admin_task["id"]], "owner": department_peer_name, "comment": "纯协作者不得替换负责人"}, expected=(403,))
            call("POST", f"/investigations/{company_collab_admin_task['id']}/assign", {"investigator": department_peer_name, "comment": "纯协作者不得借调查入口替换负责人"}, expected=(404,))
            call("PATCH", f"/records/{company_collab_admin_task['id']}", {"owner": department_peer_name}, expected=(404,))
            call("POST", f"/records/{company_collab_admin_task['id']}/transition", {"to_status": "处理中", "comment": "纯协作者不得借通用入口改状态"}, expected=(404,))
            call("DELETE", f"/records/{company_collab_admin_task['id']}", expected=(403,))
            pure_company_delete = call("POST", "/investigations/batch-delete", {"record_ids": [company_collab_admin_task["id"]]})
            assert pure_company_delete["deleted"] == 0 and pure_company_delete["failed"] == 1
        finally:
            TOKEN = admin_token
        records.append(department_peer_task["id"])
        assert outside_task["id"] in {x["id"] for x in call("GET", "/tasks?scope=mine")["items"]}
        assert outside_task["id"] in {x["id"] for x in call("GET", "/tasks?scope=department")["items"]}
        assert outside_task["id"] in {x["id"] for x in call("GET", "/tasks?scope=company")["items"]}
        admin_department_initiated_ids = {x["id"] for x in call("GET", "/tasks?scope=department&relation=initiated")["items"]}
        assert outside_task["id"] in admin_department_initiated_ids and department_peer_task["id"] in admin_department_initiated_ids
        admin_department_owned_ids = {x["id"] for x in call("GET", "/tasks?scope=department&relation=owned")["items"]}
        assert outside_task["id"] in admin_department_owned_ids and department_peer_task["id"] in admin_department_owned_ids
        admin_department_collab_ids = {x["id"] for x in call("GET", "/tasks?scope=department&relation=collaborating")["items"]}
        assert department_collab_task["id"] in admin_department_collab_ids
        admin_company_initiated_ids = {x["id"] for x in call("GET", "/tasks?scope=company&relation=initiated&page_size=200")["items"]}
        assert {outside_task["id"], department_collab_task["id"], department_peer_task["id"]}.issubset(admin_company_initiated_ids)
        admin_company_owned_ids = {x["id"] for x in call("GET", "/tasks?scope=company&relation=owned&page_size=200")["items"]}
        assert {outside_task["id"], company_owned_lifecycle_task["id"], department_collab_task["id"], department_peer_task["id"]}.issubset(admin_company_owned_ids)
        admin_company_collab_ids = {x["id"] for x in call("GET", "/tasks?scope=company&relation=collaborating&page_size=200")["items"]}
        assert company_collab_admin_task["id"] in admin_company_collab_ids
        # current_identity 必须以数据库当前角色为准，而非信任旧 JWT 中的 role：旧经理会话
        # 晋升后立即获得 admin 全所范围，降回经理后同一会话立即失去该范围。
        call("PATCH", f"/system/users/{peer_manager['id']}", {"role": "admin"})
        try:
            TOKEN = peer_manager_token
            assert call("GET", "/auth/me")["role"] == "admin"
            promoted_company_ids = {x["id"] for x in call("GET", "/tasks?scope=company&relation=initiated&page_size=200")["items"]}
            assert {outside_task["id"], department_collab_task["id"], department_peer_task["id"]}.issubset(promoted_company_ids)
            promoted_owned_ids = {x["id"] for x in call("GET", "/tasks?scope=company&relation=owned&page_size=200")["items"]}
            assert company_owned_lifecycle_task["id"] in promoted_owned_ids
            promoted_collab_ids = {x["id"] for x in call("GET", "/tasks?scope=company&relation=collaborating&page_size=200")["items"]}
            assert company_collab_admin_task["id"] in promoted_collab_ids
        finally:
            TOKEN = admin_token
            call("PATCH", f"/system/users/{peer_manager['id']}", {"role": "manager"})
        try:
            TOKEN = peer_manager_token
            assert call("GET", "/auth/me")["role"] == "manager"
            call("GET", "/tasks?scope=company&relation=initiated", expected=(403,))
            call("GET", "/tasks?scope=company&relation=owned", expected=(403,))
            call("GET", "/tasks?scope=company&relation=collaborating", expected=(403,))
        finally:
            TOKEN = admin_token
        # admin 既不是发起人也不是负责人，仍应保有全所生命周期覆盖权；每一步同时
        # 验证状态机边界，避免最高权限变成绕过合法状态流转的“任意改状态”。
        assert company_owned_lifecycle_task["initiator"] == manager_name and company_owned_lifecycle_task["owner"] == outsider_name
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/complete", {"comment": "待接收不得直接完成"}, expected=(409,))
        admin_rejected = call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/reject", {"comment": "管理员代表全所拒绝错误分派"})
        assert admin_rejected["status"] == "已拒绝" and admin_rejected["owner"] == outsider_name
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/accept", {"comment": "已拒绝不得接收"}, expected=(409,))
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/reject", {"comment": "已拒绝不得重复拒绝"}, expected=(409,))
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/handoff", {"recipient": member_name, "comment": "已拒绝不得交接"}, expected=(409,))
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/complete", {"comment": "已拒绝不得完成"}, expected=(409,))
        admin_resent = call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/resend", {"recipient": outsider_name, "comment": "管理员重新派发后继续验收"})
        assert admin_resent["status"] == "待接收" and admin_resent["owner"] == outsider_name
        admin_handed = call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/handoff", {"recipient": member_name, "comment": "管理员执行真实交接"})
        assert admin_handed["status"] == "待接收" and admin_handed["owner"] == member_name and admin_handed["handoff_auto_complete_at"] == str(date.today() + timedelta(days=5))
        admin_accepted = call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/accept", {"comment": "管理员执行真实接收"})
        assert admin_accepted["status"] == "处理中" and admin_accepted["owner"] == member_name
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/accept", {"comment": "处理中不得重复接收"}, expected=(409,))
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/reject", {"comment": "处理中不得拒绝"}, expected=(409,))
        admin_completed = call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/complete", {"comment": "管理员执行真实完成"})
        assert admin_completed["status"] == "已完成" and admin_completed["completion_auto_confirm_at"]
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/accept", {"comment": "已完成不得接收"}, expected=(409,))
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/reject", {"comment": "已完成不得拒绝"}, expected=(409,))
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/complete", {"comment": "已完成不得重复完成"}, expected=(409,))
        call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/handoff", {"recipient": outsider_name, "comment": "已完成不得交接"}, expected=(409,))
        admin_confirmed = call("POST", f"/tasks/{company_owned_lifecycle_task['id']}/confirm", {"comment": "管理员执行真实验收"})
        assert admin_confirmed["status"] == "已验收" and admin_confirmed["verified_at"]
        lifecycle_history = call("GET", f"/tasks/{company_owned_lifecycle_task['id']}/history")["items"]
        lifecycle_actions = {item["action"] for item in lifecycle_history if item["operator"] == USERNAME}
        assert {"拒绝任务", "重新派发任务", "任务交接", "接收任务", "提交任务完成", "验收任务"}.issubset(lifecycle_actions)
        unchanged_company_collab = call("GET", f"/records/{company_collab_admin_task['id']}")
        assert unchanged_company_collab["owner"] == outsider_name and unchanged_company_collab["status"] == "待接收"
        call("POST", f"/tasks/{company_collab_admin_task['id']}/complete", {"comment": "管理员最高权限仍受待接收状态机约束"}, expected=(409,))
        admin_collab_accepted = call("POST", f"/tasks/{company_collab_admin_task['id']}/accept", {"comment": "管理员接收全所纯协作任务"})
        assert admin_collab_accepted["status"] == "处理中" and admin_collab_accepted["owner"] == outsider_name
        call("POST", f"/tasks/{company_collab_admin_task['id']}/accept", {"comment": "处理中不得重复接收"}, expected=(409,))
        call("POST", f"/tasks/{company_collab_admin_task['id']}/reject", {"comment": "处理中不得拒绝"}, expected=(409,))
        admin_collab_handed = call("POST", f"/tasks/{company_collab_admin_task['id']}/handoff", {"recipient": member_name, "comment": "管理员交接全所纯协作任务"})
        assert admin_collab_handed["status"] == "待接收" and admin_collab_handed["owner"] == member_name
        admin_collab_reaccepted = call("POST", f"/tasks/{company_collab_admin_task['id']}/accept", {"comment": "管理员接收交接后的纯协作任务"})
        assert admin_collab_reaccepted["status"] == "处理中" and admin_collab_reaccepted["owner"] == member_name
        admin_collab_completed = call("POST", f"/tasks/{company_collab_admin_task['id']}/complete", {"comment": "管理员完成全所纯协作任务"})
        assert admin_collab_completed["status"] == "已完成" and admin_collab_completed["completion_auto_confirm_at"]
        call("POST", f"/tasks/{company_collab_admin_task['id']}/handoff", {"recipient": outsider_name, "comment": "已完成不得交接"}, expected=(409,))
        call("POST", f"/tasks/{company_collab_admin_task['id']}/complete", {"comment": "已完成不得重复完成"}, expected=(409,))
        admin_collab_confirmed = call("POST", f"/tasks/{company_collab_admin_task['id']}/confirm", {"comment": "管理员验收全所纯协作任务"})
        assert admin_collab_confirmed["status"] == "已验收"
        admin_collab_actions = {item["action"] for item in call("GET", f"/tasks/{company_collab_admin_task['id']}/history")["items"] if item["operator"] == USERNAME}
        assert {"接收任务", "任务交接", "提交任务完成", "验收任务"}.issubset(admin_collab_actions)
        admin_owned_query = urllib.parse.urlencode({"scope": "mine", "relation": "owned", "serial_no": outside_task["serial_no"], "page_size": 1})
        assert call("GET", f"/tasks?{admin_owned_query}")["items"][0]["id"] == outside_task["id"]
        for admin_relation in ["initiated", "collaborating"]:
            admin_relation_query = urllib.parse.urlencode({"scope": "mine", "relation": admin_relation, "serial_no": outside_task["serial_no"], "page_size": 1})
            assert call("GET", f"/tasks?{admin_relation_query}")["items"][0]["id"] == outside_task["id"]
        sort_title = f"SMOKE任务排序-{suffix}"
        sorted_tasks = []
        for offset in [2, 1, 1]:
            sorted_task = call("POST", "/tasks", {"title": sort_title, "owner": manager_name, "deadline": str(date.today() + timedelta(days=offset))}, expected=(201,))
            records.append(sorted_task["id"]); sorted_tasks.append(sorted_task)
        sort_base = {"scope": "company", "title": sort_title, "sort_by": "deadline", "page_size": 2}
        sorted_asc = call("GET", f"/tasks?{urllib.parse.urlencode({**sort_base, 'sort_order': 'asc'})}")
        sorted_desc = call("GET", f"/tasks?{urllib.parse.urlencode({**sort_base, 'sort_order': 'desc'})}")
        assert [item["id"] for item in sorted_asc["items"]] == sorted([sorted_tasks[1]["id"], sorted_tasks[2]["id"]])
        assert [item["id"] for item in sorted_desc["items"]] == [sorted_tasks[0]["id"], max(sorted_tasks[1]["id"], sorted_tasks[2]["id"])]
        call("POST", "/records", {"module": "task", "serial_no": serial("FAKE-TASK"), "title": "伪造任务", "status": "处理中", "owner": USERNAME, "data": {"deadline": str(date.today() + timedelta(days=31))}}, expected=(422,))
        call("POST", "/tasks", {"title": "无效负责人任务", "owner": f"missing-{suffix}", "deadline": str(date.today() + timedelta(days=3))}, expected=(422,))
        task = call("POST", "/tasks", {"title": "冒烟任务", "customer": "冒烟客户", "owner": manager_name, "collaborators": [member_name], "case_no": case["serial_no"], "deadline": str(date.today() + timedelta(days=7)), "priority": "紧急", "source": "日常任务"}, expected=(201,))
        records.append(task["id"])
        assert task["status"] == "待接收" and task["initiator"] == USERNAME and task["owner"] == manager_name and task["collaborators"] == [member_name]
        unread_task_query = urllib.parse.urlencode({"serial_no": task["serial_no"], "page": 1, "page_size": 15})
        # 未读状态严格按接收人隔离；admin 不能借最高数据权限读取他人的个人未读消息。
        assert call("GET", f"/tasks/unread-messages?{unread_task_query}")["total"] == 0
        call("GET", "/tasks/unread-messages?created_from=2026-07-02&created_to=2026-07-01", expected=(422,))
        call("GET", "/tasks/unread-messages?sort_by=owner", expected=(422,))
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            manager_unread = call("GET", f"/tasks/unread-messages?{unread_task_query}")
            assert manager_unread["total"] == 1 and manager_unread["unread_messages"] == 1
            assert manager_unread["items"][0]["id"] == task["id"] and manager_unread["items"][0]["latest_unread_message"] == "任务已分派."
            assert manager_unread["items"][0]["latest_unread_sender"] and manager_unread["items"][0]["latest_unread_at"] and manager_unread["items"][0]["unread_count"] == 1
            assert call("POST", f"/tasks/{task['id']}/messages/read")["updated"] == 1
            assert call("GET", f"/tasks/unread-messages?{unread_task_query}")["total"] == 0
        finally:
            TOKEN = admin_token
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            member_unread = call("GET", f"/tasks/unread-messages?{unread_task_query}")
            assert member_unread["total"] == 1 and member_unread["items"][0]["latest_unread_message"] == "任务已分派."
            assert call("POST", f"/tasks/{task['id']}/messages/read")["updated"] == 1
        finally:
            TOKEN = admin_token
        call("POST", f"/investigations/{task['id']}/assign", {"investigator": f"missing-{suffix}", "comment": "无效调查员不得绕过"}, expected=(422,))
        member_owned_only_task = call("POST", "/tasks", {"title": "SMOKE仅负责非协作任务", "owner": member_name, "deadline": str(date.today() + timedelta(days=4))}, expected=(201,)); records.append(member_owned_only_task["id"])
        collab_sort_title = f"SMOKE纯协作分页-{suffix}"
        collab_sort_tasks = []
        for _ in range(3):
            collab_sort_task = call("POST", "/tasks", {"title": collab_sort_title, "owner": manager_name, "collaborators": [member_name], "deadline": str(date.today() + timedelta(days=9))}, expected=(201,))
            records.append(collab_sort_task["id"]); collab_sort_tasks.append(collab_sort_task)
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            assert outside_task["id"] in {item["id"] for item in call("GET", "/tasks?scope=department")["items"]}
            assert task["id"] not in {item["id"] for item in call("GET", "/tasks?scope=department")["items"]}
            department_initiated_ids = {item["id"] for item in call("GET", "/tasks?scope=department&relation=initiated")["items"]}
            assert outside_task["id"] in department_initiated_ids and department_peer_task["id"] in department_initiated_ids
            assert task["id"] not in department_initiated_ids
            department_owned_ids = {item["id"] for item in call("GET", "/tasks?scope=department&relation=owned")["items"]}
            assert outside_task["id"] in department_owned_ids and task["id"] in department_owned_ids
            assert department_peer_task["id"] not in department_owned_ids
            department_collaborating_ids = {item["id"] for item in call("GET", "/tasks?scope=department&relation=collaborating")["items"]}
            assert department_collab_task["id"] in department_collaborating_ids
            assert outside_task["id"] not in department_collaborating_ids and task["id"] not in department_collaborating_ids
            call("POST", f"/tasks/{collab_sort_tasks[0]['id']}/accept", {"comment": "协作分页状态计数"})
        finally:
            TOKEN = admin_token
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            unread_collab_base = {"title": collab_sort_title, "page_size": 2}
            unread_collab_first = call("GET", f"/tasks/unread-messages?{urllib.parse.urlencode({**unread_collab_base, 'page': 1})}")
            unread_collab_second = call("GET", f"/tasks/unread-messages?{urllib.parse.urlencode({**unread_collab_base, 'page': 2})}")
            assert unread_collab_first["total"] == 3 and unread_collab_first["unread_messages"] == 4 and len(unread_collab_first["items"]) == 2
            assert len(unread_collab_second["items"]) == 1 and not ({item["id"] for item in unread_collab_first["items"]} & {item["id"] for item in unread_collab_second["items"]})
            unread_collab_sorted = call("GET", f"/tasks/unread-messages?{urllib.parse.urlencode({**unread_collab_base, 'page_size': 3, 'sort_by': 'deadline', 'sort_order': 'asc'})}")
            assert [item["id"] for item in unread_collab_sorted["items"]] == sorted(item["id"] for item in collab_sort_tasks)
            initiator_batch_task = call("POST", "/tasks", {"title": "发起人批量修改任务", "owner": manager_name, "deadline": str(date.today() + timedelta(days=6)), "priority": "普通"}, expected=(201,))
            records.append(initiator_batch_task["id"])
            call("POST", "/tasks/batch-update", {"task_ids": [initiator_batch_task["id"]], "owner": f"missing-{suffix}"}, expected=(422,))
            initiator_batch_updated = call("POST", "/tasks/batch-update", {"task_ids": [initiator_batch_task["id"]], "priority": "重要", "comment": "非负责人发起人批量修改权限验收"})
        finally:
            TOKEN = admin_token
        assert initiator_batch_updated["updated"] == 1 and initiator_batch_updated["items"][0]["priority"] == "重要"
        initiated_query = urllib.parse.urlencode({"scope": "mine", "relation": "initiated", "serial_no": task["serial_no"], "statuses": "待接收,处理中", "page": 1, "page_size": 1})
        initiated_page = call("GET", f"/tasks?{initiated_query}")
        assert initiated_page["total"] == 1 and initiated_page["page"] == 1 and initiated_page["page_size"] == 1
        assert initiated_page["items"][0]["id"] == task["id"] and initiated_page["status_counts"]["待接收"] == 1
        call("POST", "/tasks", {"title": "超期任务应拒绝", "owner": USERNAME, "deadline": str(date.today() + timedelta(days=31))}, expected=(422,))
        batch_updated = call("POST", "/tasks/batch-update", {"task_ids": [task["id"]], "priority": "重要", "deadline": str(date.today() + timedelta(days=10)), "comment": "任务更多操作批量修改验收"})
        assert batch_updated["updated"] == 1 and batch_updated["items"][0]["priority"] == "重要"
        call("POST", "/tasks/batch-update", {"task_ids": [task["id"]], "deadline": str(date.today() + timedelta(days=31))}, expected=(422,))
        call("PATCH", f"/records/{task['id']}", {"status": "已完成"}, expected=(409,))
        call("POST", f"/records/{task['id']}/transition", {"to_status": "处理中", "comment": "通用流转绕过"}, expected=(409,))

        reminder_title = f"SMOKE任务提醒专项-{suffix}"
        manager_tomorrow = call("POST", "/tasks", {"title": reminder_title, "owner": manager_name, "deadline": str(date.today() + timedelta(days=1)), "priority": "重要"}, expected=(201,)); records.append(manager_tomorrow["id"])
        member_tomorrow = call("POST", "/tasks", {"title": reminder_title, "owner": member_name, "deadline": str(date.today() + timedelta(days=1)), "priority": "重要"}, expected=(201,)); records.append(member_tomorrow["id"])
        manager_overdue3 = call("POST", "/tasks", {"title": reminder_title, "owner": manager_name, "deadline": str(date.today()), "priority": "紧急"}, expected=(201,)); records.append(manager_overdue3["id"])
        manager_overdue2 = call("POST", "/tasks", {"title": reminder_title, "owner": manager_name, "deadline": str(date.today()), "priority": "普通"}, expected=(201,)); records.append(manager_overdue2["id"])
        manager_today = call("POST", "/tasks", {"title": reminder_title, "owner": manager_name, "deadline": str(date.today()), "priority": "普通"}, expected=(201,)); records.append(manager_today["id"])
        set_task_test_data(manager_overdue3["id"], {"deadline": str(date.today() - timedelta(days=3))})
        set_task_test_data(manager_overdue2["id"], {"deadline": str(date.today() - timedelta(days=2))})

        reminder_task_query = {"scope": "company", "reminder_only": "true", "title": reminder_title, "sort_by": "deadline", "sort_order": "asc", "page_size": 2}
        reminder_tasks_first = call("GET", f"/tasks?{urllib.parse.urlencode({**reminder_task_query, 'page': 1})}")
        reminder_tasks_second = call("GET", f"/tasks?{urllib.parse.urlencode({**reminder_task_query, 'page': 2})}")
        reminder_ids = {manager_tomorrow["id"], member_tomorrow["id"], manager_overdue3["id"]}
        assert reminder_tasks_first["total"] == 3 and reminder_tasks_first["status_counts"] == {"已逾期": 1, "待接收": 2}
        actual_reminder_ids = {item["id"] for item in reminder_tasks_first["items"] + reminder_tasks_second["items"]}
        assert actual_reminder_ids == reminder_ids, {"expected": reminder_ids, "actual": actual_reminder_ids}
        assert manager_overdue2["id"] not in reminder_ids and manager_today["id"] not in reminder_ids
        assert reminder_tasks_first["summary"]["total"] == reminder_tasks_first["summary"]["reminders"]

        # 先由普通用户触发同步，再由管理员触发；两者必须得到各自独立的提醒，
        # 防止全局唯一 source_key 导致“先访问者抢走提醒”。
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            manager_task_page = call("GET", f"/tasks?{urllib.parse.urlencode({'scope': 'mine', 'relation': 'owned', 'reminder_only': 'true', 'title': reminder_title, 'page_size': 10})}")
            assert manager_task_page["total"] == 2 and {item["id"] for item in manager_task_page["items"]} == {manager_tomorrow["id"], manager_overdue3["id"]}
            manager_notice_page = call("GET", f"/notifications?{urllib.parse.urlencode({'reminder_only': 'true', 'source_type': 'task', 'keyword': reminder_title, 'page_size': 10})}")
            assert manager_notice_page["total"] == 2 and {item["source_id"] for item in manager_notice_page["items"]} == {manager_tomorrow["id"], manager_overdue3["id"]}
            assert {item["level"] for item in manager_notice_page["items"]} == {"warning", "error"}
        finally:
            TOKEN = admin_token
        admin_notice_first = call("GET", f"/notifications?{urllib.parse.urlencode({'reminder_only': 'true', 'source_type': 'task', 'keyword': reminder_title, 'page': 1, 'page_size': 1})}")
        admin_notice_second = call("GET", f"/notifications?{urllib.parse.urlencode({'reminder_only': 'true', 'source_type': 'task', 'keyword': reminder_title, 'page': 2, 'page_size': 1})}")
        assert admin_notice_first["total"] == 3 and admin_notice_first["page"] == 1 and admin_notice_first["page_size"] == 1
        assert admin_notice_second["total"] == 3 and admin_notice_first["items"][0]["id"] != admin_notice_second["items"][0]["id"]
        admin_error_notices = call("GET", f"/notifications?{urllib.parse.urlencode({'reminder_only': 'true', 'keyword': reminder_title, 'level': 'error', 'read_status': '未读', 'page_size': 10})}")
        assert admin_error_notices["total"] == 1 and admin_error_notices["items"][0]["source_id"] == manager_overdue3["id"]
        assert admin_error_notices["items"][0]["title"] == "已逾期 3 天，今日提醒"
        admin_notice_id = admin_error_notices["items"][0]["id"]
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            call("POST", f"/notifications/{admin_notice_id}/read", expected=(404,))
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            member_notice_page = call("GET", f"/notifications?{urllib.parse.urlencode({'reminder_only': 'true', 'keyword': reminder_title, 'page_size': 10})}")
            assert member_notice_page["total"] == 1 and member_notice_page["items"][0]["source_id"] == member_tomorrow["id"]
            TOKEN = login(outsider_name, "SmokePass2026!")["access_token"]
            outsider_task_page = call("GET", f"/tasks?{urllib.parse.urlencode({'scope': 'mine', 'reminder_only': 'true', 'title': reminder_title, 'page_size': 10})}")
            outsider_notice_page = call("GET", f"/notifications?{urllib.parse.urlencode({'reminder_only': 'true', 'keyword': reminder_title, 'page_size': 10})}")
            assert outsider_task_page["total"] == 0 and outsider_notice_page["total"] == 0
        finally:
            TOKEN = admin_token
        assert call("POST", f"/notifications/{admin_notice_id}/read")["is_read"] is True
        admin_read_page = call("GET", f"/notifications?{urllib.parse.urlencode({'reminder_only': 'true', 'keyword': reminder_title, 'level': 'error', 'read_status': '已读', 'page_size': 10})}")
        assert admin_read_page["total"] == 1 and admin_read_page["items"][0]["id"] == admin_notice_id
        call("GET", "/notifications?source_type=unknown", expected=(422,))
        call("GET", "/notifications?level=critical", expected=(422,))
        call("GET", "/notifications?date_from=2026-07-02&date_to=2026-07-01", expected=(422,))

        auto_task = call("POST", "/tasks", {"title": "SMOKE交接五日自动完成", "owner": manager_name, "deadline": str(date.today() + timedelta(days=5))}, expected=(201,)); records.append(auto_task["id"])
        overdue_task = call("POST", "/tasks", {"title": "SMOKE逾期错误提醒", "owner": manager_name, "deadline": str(date.today())}, expected=(201,)); records.append(overdue_task["id"])
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{auto_task['id']}/accept", {"comment": "接收后转交"})
            call("POST", f"/tasks/{auto_task['id']}/handoff", {"recipient": member_name, "comment": "验证五日自动完成"})
        finally:
            TOKEN = admin_token
        set_task_test_data(auto_task["id"], {"handoff_auto_complete_at": str(date.today() - timedelta(days=1))})
        auto_completed_page = call("GET", f"/tasks?{urllib.parse.urlencode({'scope': 'company', 'serial_no': auto_task['serial_no'], 'page_size': 1})}")
        assert auto_completed_page["items"][0]["status"] == "已完成" and auto_completed_page["items"][0]["auto_completed"] is True
        set_task_test_data(overdue_task["id"], {"deadline": str(date.today() - timedelta(days=3))})
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{auto_task['id']}/restart", {"comment": "自动完成任务不得重启"}, expected=(409,))
            auto_task_notices = [item for item in call("GET", "/notifications")["items"] if item.get("source_id") == auto_task["id"]]
            assert any(item["content"] == "任务已自动完成." and item["is_read"] is False for item in auto_task_notices)
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            overdue_notice = next(item for item in call("GET", "/notifications")["items"] if item.get("source_id") == overdue_task["id"])
            assert overdue_notice["level"] == "error"
            overdue_unread_query = urllib.parse.urlencode({"serial_no": overdue_task["serial_no"], "page_size": 1})
            overdue_unread_task = call("GET", f"/tasks/unread-messages?{overdue_unread_query}")
            assert overdue_unread_task["total"] == 1 and overdue_unread_task["items"][0]["latest_unread_message"] == "任务已分派."
            overdue_event_id = call("GET", f"/tasks/{overdue_task['id']}/history")["items"][0]["id"]
            overdue_manual_notice = call("POST", f"/tasks/{overdue_task['id']}/history/{overdue_event_id}/mark-unread")
            call("POST", f"/tasks/{overdue_task['id']}/accept", {"comment": "逾期任务接收"})
            call("POST", f"/tasks/{overdue_task['id']}/complete", {"comment": "逾期任务完成待验收"})
        finally:
            TOKEN = admin_token
        call("POST", f"/tasks/{overdue_task['id']}/confirm", {"comment": "逾期任务验收"})
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            overdue_terminal_notifications = call("GET", "/notifications")["items"]
            assert all(item["id"] != overdue_notice["id"] for item in overdue_terminal_notifications)
            assert any(item["id"] == overdue_manual_notice["id"] and item["is_read"] is False for item in overdue_terminal_notifications)
        finally:
            TOKEN = admin_token
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            owned_query = urllib.parse.urlencode({"scope": "mine", "relation": "owned", "serial_no": task["serial_no"], "page_size": 1})
            owned_page = call("GET", f"/tasks?{owned_query}")
            assert owned_page["total"] == 1 and owned_page["items"][0]["id"] == task["id"]
            accepted = call("POST", f"/tasks/{task['id']}/accept", {"comment": "负责人接收"})
        finally:
            TOKEN = admin_token
        assert accepted["status"] == "处理中"
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            initiated_only_query = urllib.parse.urlencode({"scope": "mine", "relation": "collaborating", "serial_no": initiator_batch_task["serial_no"], "page_size": 1})
            owned_only_query = urllib.parse.urlencode({"scope": "mine", "relation": "collaborating", "serial_no": member_owned_only_task["serial_no"], "page_size": 1})
            assert call("GET", f"/tasks?{initiated_only_query}")["total"] == 0
            assert call("GET", f"/tasks?{owned_only_query}")["total"] == 0
            collab_page_base = {"scope": "mine", "relation": "collaborating", "title": collab_sort_title, "sort_by": "deadline", "sort_order": "asc", "page_size": 2}
            collab_first_page = call("GET", f"/tasks?{urllib.parse.urlencode({**collab_page_base, 'page': 1})}")
            collab_second_page = call("GET", f"/tasks?{urllib.parse.urlencode({**collab_page_base, 'page': 2})}")
            expected_collab_ids = sorted(item["id"] for item in collab_sort_tasks)
            assert collab_first_page["total"] == 3 and [item["id"] for item in collab_first_page["items"]] == expected_collab_ids[:2]
            assert [item["id"] for item in collab_second_page["items"]] == expected_collab_ids[2:]
            assert collab_first_page["status_counts"]["处理中"] == 1 and collab_first_page["status_counts"]["待接收"] == 2
            collaborating_query = urllib.parse.urlencode({"scope": "mine", "relation": "collaborating", "serial_no": task["serial_no"], "page_size": 1})
            collaborating_page = call("GET", f"/tasks?{collaborating_query}")
            assert collaborating_page["total"] == 1 and collaborating_page["items"][0]["id"] == task["id"]
            pure_collab_comment = call("POST", f"/tasks/{task['id']}/comments", {"comment": "纯协作人沟通"}, expected=(201,))
            assert any(item["id"] == pure_collab_comment["id"] for item in call("GET", f"/tasks/{task['id']}/history")["items"])
            pure_collab_notice = call("POST", f"/tasks/{task['id']}/history/{pure_collab_comment['id']}/mark-unread")
            assert pure_collab_notice["recipient"] == member_name and pure_collab_notice["is_read"] is False
            pure_collab_unread = call("GET", f"/tasks/unread-messages?{unread_task_query}")
            assert pure_collab_unread["total"] == 1 and pure_collab_unread["items"][0]["latest_unread_message"] == "纯协作人沟通"
            assert next(item for item in call("GET", f"/tasks/{task['id']}/history")["items"] if item["id"] == pure_collab_comment["id"])["unread"] is True
            call("POST", f"/tasks/{task['id']}/accept", {"comment": "纯协作人不得接收"}, expected=(403,))
            call("POST", f"/tasks/{task['id']}/reject", {"comment": "纯协作人不得拒绝"}, expected=(403,))
            call("POST", f"/tasks/{task['id']}/restart", {"comment": "纯协作人不得重新开始"}, expected=(403,))
            call("POST", f"/tasks/{task['id']}/complete", {"comment": "纯协作人不得完成"}, expected=(403,))
            call("POST", f"/tasks/{task['id']}/confirm", {"comment": "纯协作人不得确认"}, expected=(403,))
            call("POST", f"/tasks/{task['id']}/handoff", {"recipient": USERNAME, "comment": "协作人无权交接"}, expected=(403,))
            call("POST", "/tasks/batch-update", {"task_ids": [task["id"]], "priority": "普通", "comment": "纯协作人不得批量修改"}, expected=(403,))
            call("POST", f"/investigations/{task['id']}/assign", {"investigator": member_name, "comment": "纯协作人不得借调查入口替换负责人"}, expected=(404,))
            call("PATCH", f"/records/{task['id']}", {"owner": member_name}, expected=(404,))
            call("POST", f"/records/{task['id']}/transition", {"to_status": "已完成", "comment": "纯协作人不得借通用入口变更状态"}, expected=(404,))
            call("DELETE", f"/records/{task['id']}", expected=(403,))
            pure_collab_delete = call("POST", "/investigations/batch-delete", {"record_ids": [task["id"]]})
            assert pure_collab_delete["deleted"] == 0 and pure_collab_delete["failed"] == 1
        finally:
            TOKEN = admin_token
        unchanged_after_collab_checks = call("GET", f"/records/{task['id']}")
        assert unchanged_after_collab_checks["owner"] == manager_name and unchanged_after_collab_checks["status"] == "处理中"
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{task['id']}/handoff", {"recipient": manager_name, "comment": "禁止自交接"}, expected=(422,))
            call("POST", f"/tasks/{task['id']}/handoff", {"recipient": f"missing-{suffix}", "comment": "无效接收人"}, expected=(422,))
            handed = call("POST", f"/tasks/{task['id']}/handoff", {"recipient": member_name, "comment": "真实用户交接"})
        finally:
            TOKEN = admin_token
        assert handed["status"] == "待接收" and handed["owner"] == member_name and handed["handoff_auto_complete_at"] == str(date.today() + timedelta(days=5))
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{task['id']}/restart", {"comment": "旧负责人不得重启"}, expected=(403,))
        finally:
            TOKEN = admin_token
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            restarted = call("POST", f"/tasks/{task['id']}/restart", {"comment": "接收人重新开始"})
            set_task_test_data(task["id"], {"handoff_auto_complete_at": str(date.today() - timedelta(days=1))})
            prevented_page = call("GET", f"/tasks?{urllib.parse.urlencode({'scope': 'mine', 'serial_no': task['serial_no'], 'page_size': 1})}")
            assert prevented_page["items"][0]["status"] == "处理中" and prevented_page["items"][0]["auto_completed"] is False
            comment_event = call("POST", f"/tasks/{task['id']}/comments", {"comment": "沟通记录"}, expected=(201,))
            unread_notice = call("POST", f"/tasks/{task['id']}/history/{comment_event['id']}/mark-unread")
            repeated_notice = call("POST", f"/tasks/{task['id']}/history/{comment_event['id']}/mark-unread")
            assert repeated_notice["id"] == unread_notice["id"] and repeated_notice["is_read"] is False
            assert call("POST", f"/notifications/{unread_notice['id']}/read")["is_read"] is True
            restored_notice = call("POST", f"/tasks/{task['id']}/history/{comment_event['id']}/mark-unread")
            assert restored_notice["id"] == unread_notice["id"] and restored_notice["is_read"] is False
            completed = call("POST", f"/tasks/{task['id']}/complete", {"comment": "完成"})
        finally:
            TOKEN = admin_token
        try:
            TOKEN = login(outsider_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{task['id']}/history/{comment_event['id']}/mark-unread", expected=(403,))
            assert call("GET", f"/tasks/unread-messages?{unread_task_query}")["total"] == 0
            call("POST", f"/tasks/{task['id']}/messages/read", expected=(403,))
        finally:
            TOKEN = admin_token
        outside_event_id = call("GET", f"/tasks/{outside_task['id']}/history")["items"][0]["id"]
        call("POST", f"/tasks/{task['id']}/history/{outside_event_id}/mark-unread", expected=(404,))
        assert restarted["status"] == "处理中"
        assert completed["status"] == "已完成" and completed["workflow_status"] == "已完成" and completed["completion_auto_confirm_at"] and not completed["verified_at"]
        completed_query = urllib.parse.urlencode({"scope": "mine", "relation": "initiated", "serial_no": task["serial_no"], "statuses": "已完成", "page_size": 1})
        completed_page = call("GET", f"/tasks?{completed_query}")
        assert completed_page["total"] == 1 and completed_page["items"][0]["id"] == task["id"] and completed_page["status_counts"]["已完成"] == 1
        restarted_by_initiator = call("POST", f"/tasks/{task['id']}/restart", {"comment": "验收退回"})
        assert restarted_by_initiator["status"] == "处理中"
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{task['id']}/complete", {"comment": "再次完成"})
        finally:
            TOKEN = admin_token
        confirmed = call("POST", f"/tasks/{task['id']}/confirm", {"comment": "确认完成"})
        assert confirmed["status"] == "已验收" and confirmed["workflow_status"] == "已验收" and confirmed["verified_at"] and not confirmed["completion_auto_confirm_at"]
        verified_query = urllib.parse.urlencode({"scope": "mine", "relation": "initiated", "serial_no": task["serial_no"], "statuses": "已验收", "page_size": 1})
        verified_page = call("GET", f"/tasks?{verified_query}")
        assert verified_page["total"] == 1 and verified_page["items"][0]["id"] == task["id"] and verified_page["status_counts"]["已验收"] == 1
        call("POST", "/tasks/batch-update", {"task_ids": [task["id"]], "priority": "普通", "comment": "终态不得批量修改"}, expected=(409,))
        call("POST", f"/tasks/{task['id']}/handoff", {"recipient": manager_name, "comment": "已验收不得转交"}, expected=(409,))
        call("POST", f"/investigations/{task['id']}/assign", {"investigator": manager_name, "comment": "已验收不得绕过改派"}, expected=(409,))
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            terminal_unread_page = call("GET", f"/tasks/unread-messages?{unread_task_query}")
            assert terminal_unread_page["total"] == 1 and terminal_unread_page["items"][0]["latest_unread_message"] == "任务已确认完成."
            assert terminal_unread_page["items"][0]["unread_count"] >= 3
            assert call("POST", f"/tasks/{task['id']}/messages/read")["updated"] >= 3
            assert call("GET", f"/tasks/unread-messages?{unread_task_query}")["total"] == 0
            terminal_notifications = call("GET", "/notifications")["items"]
            assert any(item["id"] == unread_notice["id"] and item["is_read"] is True for item in terminal_notifications)
            assert any(item["id"] == pure_collab_notice["id"] and item["is_read"] is True for item in terminal_notifications)
        finally:
            TOKEN = admin_token
        assert len(call("GET", f"/tasks/{task['id']}/history")["items"]) >= 7
        # 任务撤回必须走专用闭环：普通发起人可撤回待接收任务，管理员可撤回处理中任务；
        # 负责人、通用流转和重复操作均不能绕过状态与权限限制。
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            initiator_withdraw_task = call("POST", "/tasks", {"title": "SMOKE发起人撤回任务", "owner": member_name, "deadline": str(date.today() + timedelta(days=3))}, expected=(201,))
            records.append(initiator_withdraw_task["id"])
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{initiator_withdraw_task['id']}/withdraw", {"comment": "负责人不能撤回发起人任务"}, expected=(403,))
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{initiator_withdraw_task['id']}/withdraw", {"comment": ""}, expected=(422,))
            withdrawn_by_initiator = call("POST", f"/tasks/{initiator_withdraw_task['id']}/withdraw", {"comment": "工作安排取消"})
            initiated_withdrawn_page = call("GET", f"/tasks?{urllib.parse.urlencode({'scope': 'mine', 'relation': 'initiated', 'serial_no': initiator_withdraw_task['serial_no'], 'statuses': '已撤回', 'page_size': 10})}")
        finally:
            TOKEN = admin_token
        assert withdrawn_by_initiator["status"] == "已撤回" and withdrawn_by_initiator["workflow_status"] == "已撤回"
        assert initiated_withdrawn_page["total"] == 1 and initiated_withdrawn_page["items"][0]["id"] == initiator_withdraw_task["id"]
        initiator_withdraw_history = call("GET", f"/tasks/{initiator_withdraw_task['id']}/history")["items"]
        assert any(item["action"] == "撤回任务" and item["to_status"] == "已撤回" and item["comment"] == "工作安排取消" for item in initiator_withdraw_history)
        admin_withdraw_task = call("POST", "/tasks", {"title": "SMOKE管理员撤回处理中任务", "owner": member_name, "deadline": str(date.today() + timedelta(days=3))}, expected=(201,))
        records.append(admin_withdraw_task["id"])
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{admin_withdraw_task['id']}/accept", {"comment": "先进入处理中验证管理员撤回"})
        finally:
            TOKEN = admin_token
        withdrawn_by_admin = call("POST", f"/tasks/{admin_withdraw_task['id']}/withdraw", {"comment": "管理员终止当前安排"})
        assert withdrawn_by_admin["status"] == "已撤回" and withdrawn_by_admin["workflow_status"] == "已撤回"
        call("POST", f"/tasks/{admin_withdraw_task['id']}/withdraw", {"comment": "重复撤回"}, expected=(409,))
        call("POST", f"/records/{admin_withdraw_task['id']}/transition", {"to_status": "处理中", "comment": "通用流转不得绕过任务撤回"}, expected=(409,))
        rejected_task = call("POST", "/tasks", {"title": "冒烟拒绝任务", "owner": manager_name, "deadline": str(date.today() + timedelta(days=3))}, expected=(201,)); records.append(rejected_task["id"])
        try:
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            call("POST", f"/tasks/{rejected_task['id']}/reject", {"comment": ""}, expected=(422,))
            rejected = call("POST", f"/tasks/{rejected_task['id']}/reject", {"comment": "负责人不匹配"})
            call("POST", f"/tasks/{rejected_task['id']}/resend", {"recipient": member_name, "comment": "负责人无权重新派发"}, expected=(403,))
        finally:
            TOKEN = admin_token
        assert rejected["status"] == "已拒绝" and rejected["rejected_reason"] and not rejected["handoff_auto_complete_at"]
        call("POST", f"/tasks/{rejected_task['id']}/resend", {"recipient": f"missing-{suffix}", "comment": "无效新负责人"}, expected=(422,))
        resent = call("POST", f"/tasks/{rejected_task['id']}/resend", {"recipient": member_name, "comment": "重新派发"})
        assert resent["status"] == "待接收" and resent["owner"] == member_name and resent["handoff_auto_complete_at"] == str(date.today() + timedelta(days=5))
        # 批量生命周期必须逐条校验、整批原子：接收、交接、完成、撤回均走专用接口，
        # 不能通过批量字段修改或通用 records 流转替代。
        batch_lifecycle_tasks = [
            call("POST", "/tasks", {"title": f"SMOKE批量生命周期{i}", "owner": member_name, "deadline": str(date.today() + timedelta(days=3))}, expected=(201,))
            for i in (1, 2)
        ]
        records.extend(item["id"] for item in batch_lifecycle_tasks)
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            batch_accepted = call("POST", "/tasks/batch-lifecycle", {"task_ids": [item["id"] for item in batch_lifecycle_tasks], "action": "accept", "comment": "批量接收验收"})
            assert batch_accepted["updated"] == 2 and all(item["status"] == "处理中" for item in batch_accepted["items"])
            call("POST", "/tasks/batch-lifecycle", {"task_ids": [item["id"] for item in batch_lifecycle_tasks], "action": "accept"}, expected=(409,))
            batch_handed = call("POST", "/tasks/batch-lifecycle", {"task_ids": [item["id"] for item in batch_lifecycle_tasks], "action": "handoff", "recipient": manager_name, "comment": "批量交接验收"})
            assert all(item["status"] == "待接收" and item["owner"] == manager_name and item["handoff_auto_complete_at"] == str(date.today() + timedelta(days=5)) for item in batch_handed["items"])
            TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
            batch_reaccepted = call("POST", "/tasks/batch-lifecycle", {"task_ids": [item["id"] for item in batch_lifecycle_tasks], "action": "accept"})
            assert all(item["status"] == "处理中" for item in batch_reaccepted["items"])
            batch_completed = call("POST", "/tasks/batch-lifecycle", {"task_ids": [item["id"] for item in batch_lifecycle_tasks], "action": "complete", "comment": "批量成果已提交"})
            assert all(item["status"] == "已完成" and item["completion_auto_confirm_at"] for item in batch_completed["items"])
        finally:
            TOKEN = admin_token
        batch_withdraw_tasks = [
            call("POST", "/tasks", {"title": f"SMOKE批量撤回{i}", "owner": member_name, "deadline": str(date.today() + timedelta(days=3))}, expected=(201,))
            for i in (1, 2)
        ]
        records.extend(item["id"] for item in batch_withdraw_tasks)
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            call("POST", "/tasks/batch-lifecycle", {"task_ids": [item["id"] for item in batch_withdraw_tasks], "action": "withdraw", "comment": "负责人不可批量撤回"}, expected=(403,))
        finally:
            TOKEN = admin_token
        call("POST", "/tasks/batch-lifecycle", {"task_ids": [item["id"] for item in batch_withdraw_tasks], "action": "withdraw", "comment": ""}, expected=(422,))
        batch_withdrawn = call("POST", "/tasks/batch-lifecycle", {"task_ids": [item["id"] for item in batch_withdraw_tasks], "action": "withdraw", "comment": "批量撤回验收"})
        assert all(item["status"] == "已撤回" for item in batch_withdrawn["items"])
        batch_withdraw_history = call("GET", f"/tasks/{batch_withdraw_tasks[0]['id']}/history")["items"]
        assert any(item["action"] == "批量撤回任务" and item["comment"] == "批量撤回验收" for item in batch_withdraw_history)
        passed("任务管理员全所关系、纯协作隔离/权限、稳定排序、分页状态计数、发起人/管理员专用撤回、真实用户及CSV校验、五日自动完成/重启阻止、历史标记未读、提醒级别、终态保护和通用接口防绕过")

        imported_reference = serial("BANK-IMPORT")
        imported_csv = ("\ufeff对方户名,银行流水号,到账日期,到账金额,摘要\n" + f"冒烟导入付款方,{imported_reference},{date.today()},123.45,银行流水导入验收\n").encode("utf-8")
        imported_result = multipart_upload("/finance/incoming-payments/import", {}, "bank-smoke.csv", imported_csv, expected=(200,))
        assert imported_result["created"] == 1 and not imported_result["errors"]
        imported_items = call("GET", f"/finance/incoming-payments?keyword={urllib.parse.quote(imported_reference)}")["items"]
        assert len(imported_items) == 1 and imported_items[0]["amount"] == 123.45
        incoming_payments.append(imported_items[0]["id"])
        duplicate_import = multipart_upload("/finance/incoming-payments/import", {}, "bank-smoke.csv", imported_csv, expected=(200,))
        assert duplicate_import["created"] == 0 and len(duplicate_import["errors"]) == 1

        receipt_plan = call("POST", "/receivables", {"contract_record_id": contract["id"], "phase": "银行回款分配验收", "due_date": str(date.today() + timedelta(days=15)), "amount": 500, "payer": "冒烟测试客户"}, expected=(201,))
        receivables.append(receipt_plan["id"])
        incoming = call("POST", "/finance/incoming-payments", {"received_date": str(date.today()), "amount": 500, "payer_name": "冒烟付款单位", "bank_reference": serial("BANK-REF"), "remark": "银行到账认领分配验收"}, expected=(201,))
        incoming_payments.append(incoming["id"])
        assert incoming["status"] == "待认领" and incoming["remaining_amount"] == 500
        TOKEN = login(member_name, "SmokePass2026!")["access_token"]
        assert all(item["id"] != incoming["id"] for item in call("GET", "/finance/incoming-payments")["items"])
        TOKEN = admin_token
        allocation_body = {"allocations": [{"receivable_plan_id": receipt_plan["id"], "amount": 300, "case_no": case["serial_no"], "payment_method": "申浩工行", "settlement_items": [{"fee_type": "一审诉讼费", "amount": 100, "settlement_amount": 100, "archive_fee": 0}, {"fee_type": "律师代理费", "amount": 200, "settlement_amount": 160, "archive_fee": 16}]}], "comment": "分配至案件首笔"}
        call("POST", f"/finance/incoming-payments/{incoming['id']}/allocate", allocation_body, expected=(409,))
        claimed_incoming = call("POST", f"/finance/incoming-payments/{incoming['id']}/claim", {"customer": "冒烟测试客户", "comment": "付款主体核对无误"})
        assert claimed_incoming["status"] == "待分配" and claimed_incoming["claimed_customer"] == "冒烟测试客户"
        partial_incoming = call("POST", f"/finance/incoming-payments/{incoming['id']}/allocate", allocation_body)
        assert partial_incoming["status"] == "部分分配" and partial_incoming["remaining_amount"] == 200
        completed_incoming = call("POST", f"/finance/incoming-payments/{incoming['id']}/allocate", {"allocations": [{"receivable_plan_id": receipt_plan["id"], "amount": 200, "case_no": case["serial_no"], "payment_method": "申浩工行", "settlement_items": [{"fee_type": "其他费用", "amount": 200, "settlement_amount": 200, "archive_fee": 0}]}], "comment": "分配剩余回款"})
        assert completed_incoming["status"] == "已分配" and completed_incoming["allocated_amount"] == 500 and len(completed_incoming["allocations"]) == 2
        updated_receipt_plan = next(item for item in call("GET", "/receivables")["items"] if item["id"] == receipt_plan["id"])
        assert updated_receipt_plan["received_amount"] == 500 and updated_receipt_plan["status"] == "已收款"
        call("POST", "/finance/transactions", {"transaction_type": "回款", "amount": 1, "transaction_date": str(date.today()), "voucher_no": "BYPASS"}, expected=(409,))
        for bypass_type in ["付款", "开票", "退费"]:
            call("POST", "/finance/transactions", {"transaction_type": bypass_type, "amount": 1, "transaction_date": str(date.today()), "voucher_no": f"BYPASS-{bypass_type}"}, expected=(409,))

        settlement_candidates = call("GET", f"/finance/general-settlements/pending?case_no={urllib.parse.quote(case['serial_no'])}&payment_method={urllib.parse.quote('申浩工行')}")
        settlement_candidate = next(item for item in settlement_candidates["items"] if item["id"] == incoming["id"])
        settlement_data = settlement_candidate["data"]
        assert settlement_data["receipt_amount"] == 500 and settlement_data["allocated_amount"] == 500 and settlement_data["remaining_amount"] == 0
        assert settlement_data["assigned_official_fee"] == 100 and settlement_data["assigned_agency_fee"] == 200 and settlement_data["assigned_other_fee"] == 200
        assert settlement_data["agency_settlement_amount"] == 160 and settlement_data["archive_fee"] == 16 and settlement_data["actual_settlement_amount"] == 444
        assert len(settlement_data["allocation_details"]) == 3 and settlement_candidates["page_size"] == 10
        call("POST", "/finance/general-settlements/apply", {"receipt_ids": []}, expected=(422,))
        call("POST", "/records", {"module": "finance_settlement", "serial_no": serial("SETTLEMENT-BYPASS"), "title": "绕过专用结算入口", "status": "待审批"}, expected=(422,))
        for export_kind in ["settlement", "receipt", "case"]:
            status_code, payload, content_type = call("GET", f"/finance/general-settlements/export?kind={export_kind}&ids={incoming['id']}", raw=True)
            assert status_code == 200 and "application/vnd.ms-excel" in content_type and payload.startswith(b"<?xml")
        applied = call("POST", "/finance/general-settlements/apply", {"receipt_ids": [incoming["id"]], "comment": "冒烟待结算提交"}, expected=(201,))
        application_id = applied["application_ids"][0]
        settlement_applications.append(application_id)
        assert call("GET", f"/records/{application_id}")["status"] == "待审批"
        audit_applications = call("GET", f"/finance/general-settlements/applications?case_no={urllib.parse.quote(case['serial_no'])}&status={urllib.parse.quote('待审批')}")
        audit_application = next(item for item in audit_applications["items"] if item["id"] == application_id)
        assert audit_application["data"]["receipt_id"] == incoming["id"] and audit_application["data"]["applied_by"] == USERNAME
        assert audit_applications["totals"]["actual_settlement_amount"] >= 444 and audit_applications["page_size"] == 10
        for export_kind in ["settlement", "receipt", "case"]:
            status_code, payload, content_type = call("GET", f"/finance/general-settlements/export?kind={export_kind}&application_ids={application_id}", raw=True)
            assert status_code == 200 and "application/vnd.ms-excel" in content_type and payload.startswith(b"<?xml")
        call("POST", "/finance/general-settlements/apply", {"receipt_ids": [incoming["id"]]}, expected=(409,))
        call("PATCH", f"/records/{application_id}", {"status": "已审批"}, expected=(409,))
        call("POST", f"/records/{application_id}/transition", {"to_status": "已审批", "comment": "绕过"}, expected=(409,))
        call("DELETE", f"/records/{application_id}", expected=(409,))
        approved_settlement = call("POST", "/finance/general-settlements/applications/review", {"application_ids": [application_id], "approved": True, "comment": "同意结算冒烟验收"})
        assert approved_settlement["reviewed"] == 1 and approved_settlement["status"] == "待付款"
        approved_record = call("GET", f"/records/{application_id}")
        assert approved_record["status"] == "待付款" and approved_record["data"]["reviewer"] == USERNAME and approved_record["data"]["review_comment"] == "同意结算冒烟验收"
        assert any(item["action"] == "同意结算" and item["to_status"] == "待付款" for item in call("GET", f"/records/{application_id}/history")["items"])
        payment_applications = call("GET", f"/finance/general-settlements/applications?case_no={urllib.parse.quote(case['serial_no'])}&status={urllib.parse.quote('待付款')}")
        assert application_id in {item["id"] for item in payment_applications["items"]} and payment_applications["page_size"] == 10
        for export_kind in ["settlement", "receipt", "case"]:
            status_code, payload, content_type = call("GET", f"/finance/general-settlements/export?kind={export_kind}&application_ids={application_id}", raw=True)
            assert status_code == 200 and "application/vnd.ms-excel" in content_type and payload.startswith(b"<?xml")
        call("POST", "/finance/general-settlements/applications/review", {"application_ids": [application_id], "approved": True, "comment": "重复审批"}, expected=(409,))
        call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [], "action": "paid"}, expected=(422,))
        call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [application_id], "action": "rollback", "comment": ""}, expected=(422,))
        rolled_back = call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [application_id], "action": "rollback", "comment": "回退补充结算资料"})
        assert rolled_back["processed"] == 1 and rolled_back["status"] == "已退回"
        rolled_back_record = call("GET", f"/records/{application_id}")
        assert rolled_back_record["status"] == "已退回" and rolled_back_record["data"]["rejection_comment"] == "回退补充结算资料" and rolled_back_record["data"]["rollback_by"] == USERNAME
        assert any(item["action"] == "回退结算" and item["to_status"] == "已退回" for item in call("GET", f"/records/{application_id}/history")["items"])
        rejected_statuses = urllib.parse.quote("已拒绝,已退回,已驳回")
        returned_in_rejected = call("GET", f"/finance/general-settlements/applications?case_no={urllib.parse.quote(case['serial_no'])}&status={rejected_statuses}")
        assert application_id in {item["id"] for item in returned_in_rejected["items"]}
        call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [application_id], "action": "paid"}, expected=(409,))
        call("DELETE", f"/finance/general-settlements/applications/{application_id}", expected=(204,))
        settlement_applications.remove(application_id)
        restored_candidates = call("GET", f"/finance/general-settlements/pending?case_no={urllib.parse.quote(case['serial_no'])}")
        assert incoming["id"] in {item["id"] for item in restored_candidates["items"]}
        rejected_applied = call("POST", "/finance/general-settlements/apply", {"receipt_ids": [incoming["id"]], "comment": "拒绝结算流程验收"}, expected=(201,))
        rejected_application_id = rejected_applied["application_ids"][0]
        settlement_applications.append(rejected_application_id)
        rejected_settlement = call("POST", "/finance/general-settlements/applications/review", {"application_ids": [rejected_application_id], "approved": False, "comment": "结算资料需补充"})
        assert rejected_settlement["status"] == "已拒绝"
        rejected_record = call("GET", f"/records/{rejected_application_id}")
        assert rejected_record["status"] == "已拒绝" and rejected_record["data"]["review_comment"] == "结算资料需补充"
        rejected_list = call("GET", f"/finance/general-settlements/applications?case_no={urllib.parse.quote(case['serial_no'])}&status={urllib.parse.quote('已拒绝')}")
        assert rejected_application_id in {item["id"] for item in rejected_list["items"]}
        restored_after_reject = call("GET", f"/finance/general-settlements/pending?case_no={urllib.parse.quote(case['serial_no'])}")
        assert incoming["id"] in {item["id"] for item in restored_after_reject["items"]}
        call("POST", "/finance/general-settlements/applications/reapply", {"application_ids": [], "comment": "重新申请"}, expected=(422,))
        call("POST", "/finance/general-settlements/applications/reapply", {"application_ids": [rejected_application_id], "comment": "   "}, expected=(422,))
        reapplied = call("POST", "/finance/general-settlements/applications/reapply", {"application_ids": [rejected_application_id], "comment": "补正结算资料后重新申请"})
        assert reapplied["reapplied"] == 1 and reapplied["status"] == "待审批"
        reapplied_record = call("GET", f"/records/{rejected_application_id}")
        assert reapplied_record["status"] == "待审批" and reapplied_record["data"]["reapplied_by"] == USERNAME and reapplied_record["data"]["reapply_comment"] == "补正结算资料后重新申请"
        assert any(item["action"] == "重新申请结算" and item["from_status"] == "已拒绝" and item["to_status"] == "待审批" for item in call("GET", f"/records/{rejected_application_id}/history")["items"])
        call("POST", "/finance/general-settlements/applications/reapply", {"application_ids": [rejected_application_id], "comment": "重复重新申请"}, expected=(409,))
        pending_after_reapply = call("GET", f"/finance/general-settlements/applications?case_no={urllib.parse.quote(case['serial_no'])}&status={urllib.parse.quote('待审批')}")
        assert rejected_application_id in {item["id"] for item in pending_after_reapply["items"]}
        candidate_after_reapply = call("GET", f"/finance/general-settlements/pending?case_no={urllib.parse.quote(case['serial_no'])}")
        assert incoming["id"] not in {item["id"] for item in candidate_after_reapply["items"]}
        call("DELETE", f"/finance/general-settlements/applications/{rejected_application_id}", expected=(204,))
        settlement_applications.remove(rejected_application_id)
        paid_applied = call("POST", "/finance/general-settlements/apply", {"receipt_ids": [incoming["id"]], "comment": "结算付款流程验收"}, expected=(201,))
        paid_application_id = paid_applied["application_ids"][0]
        settlement_applications.append(paid_application_id)
        call("POST", "/finance/general-settlements/applications/review", {"application_ids": [paid_application_id], "approved": True, "comment": "付款前审核通过"})
        paid_result = call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [paid_application_id], "action": "paid", "comment": "银行支付完成"})
        assert paid_result["processed"] == 1 and paid_result["status"] == "已付款"
        paid_record = call("GET", f"/records/{paid_application_id}")
        assert paid_record["status"] == "已付款" and paid_record["data"]["paid_by"] == USERNAME and paid_record["data"]["paid_comment"] == "银行支付完成" and paid_record["data"]["paid_at"]
        assert any(item["action"] == "标记已支付" and item["to_status"] == "已付款" for item in call("GET", f"/records/{paid_application_id}/history")["items"])
        today_text = str(date.today())
        paid_list = call("GET", f"/finance/general-settlements/applications?case_no={urllib.parse.quote(case['serial_no'])}&status={urllib.parse.quote('已付款')}&paid_from={today_text}&paid_to={today_text}")
        assert paid_application_id in {item["id"] for item in paid_list["items"]}
        archive_pending = call("GET", f"/finance/archive-settlements/pending?case_no={urllib.parse.quote(case['serial_no'])}&case_type={urllib.parse.quote('刑事案件')}&settled_from={today_text}&settled_to={today_text}")
        assert archive_pending["total"] == 1 and archive_pending["page_size"] == 10
        archive_pending_row = archive_pending["items"][0]
        assert archive_pending_row["status"] == "待归档" and archive_pending_row["data"]["application_id"] == paid_application_id
        assert archive_pending_row["data"]["fee_type"] == "律师代理费" and archive_pending_row["data"]["receipt_amount"] == 200 and archive_pending_row["data"]["archive_fee_amount"] == 16
        assert archive_pending["totals"]["receipt_amount"] == 200 and archive_pending["totals"]["archive_fee_amount"] == 16
        call("GET", "/finance/archive-settlements/pending?received_from=2026-12-31&received_to=2026-01-01", expected=(422,))
        call("GET", "/finance/archive-settlements/export", expected=(422,))
        status_code, payload, content_type = call("GET", f"/finance/archive-settlements/export?ids={urllib.parse.quote(str(archive_pending_row['id']))}", raw=True)
        assert status_code == 200 and "application/vnd.ms-excel" in content_type and payload.startswith(b"<?xml")
        archive_case_payload = {
            "case_closed": True,
            "fees_settled": True,
            "documents_complete": True,
            "finance_complete": True,
            "archive_no": serial("SETTLEMENT-ARCHIVE"),
            "paper_archive_location": "冒烟归档柜 B-02",
            "paper_volume_count": 1,
            "comment": "结算归档费待支付验收",
            "submit": True,
        }
        # 案件办结必须先完成系统生成的固定任务；结算归档同样不得绕过该业务门槛。
        for fixed_task in call("GET", f"/cases/{case['id']}/tasks")["items"]:
            if fixed_task.get("data", {}).get("task_type") != "固定任务" or fixed_task["status"] in {"已完成", "已验收", "已取消"}:
                continue
            if fixed_task["status"] in {"待接收", "待接受"}:
                call("POST", f"/tasks/{fixed_task['id']}/accept", {"comment": "结算归档前办理固定任务"})
            call("POST", f"/tasks/{fixed_task['id']}/complete", {"comment": "固定任务成果已提交"})
            call("POST", f"/tasks/{fixed_task['id']}/confirm", {"comment": "案件主管验收通过"})
        call("POST", f"/cases/{case['id']}/close", {"comment": "结算归档前确认案件办结"})
        for category in ["委托材料", "证据材料", "诉讼文书", "裁判文书"]:
            settlement_archive_file = multipart_upload("/attachments", {"record_id": case["id"], "category": category, "remark": "结算归档真实条件验收"}, f"smoke-settlement-archive-{category}-{suffix}.txt", category.encode("utf-8"))
            attachments.append(settlement_archive_file["id"])
        call("POST", f"/cases/{case['id']}/archive", archive_case_payload)
        call("POST", f"/cases/{case['id']}/archive/review", {"approved": True, "comment": "归档审核通过"})
        archive_payment = call("GET", f"/finance/archive-settlements/payment?case_no={urllib.parse.quote(case['serial_no'])}&archive_from={today_text}&archive_to={today_text}")
        assert archive_payment["total"] == 1 and archive_payment["page_size"] == 10
        archive_payment_row = archive_payment["items"][0]
        assert archive_payment_row["id"] == archive_pending_row["id"] and archive_payment_row["status"] == "待支付"
        assert archive_payment_row["data"]["archive_no"] == archive_case_payload["archive_no"] and archive_payment_row["data"]["archive_status"] == "审核通过"
        assert archive_payment_row["data"]["archive_reviewer"] == USERNAME and archive_payment_row["data"]["archive_submitter"] == USERNAME
        assert archive_payment["totals"]["receipt_amount"] == 200 and archive_payment["totals"]["archive_fee_amount"] == 16
        call("GET", "/finance/archive-settlements/payment?archive_from=2026-12-31&archive_to=2026-01-01", expected=(422,))
        call("GET", "/finance/archive-settlements/payment/export", expected=(422,))
        status_code, payload, content_type = call("GET", f"/finance/archive-settlements/payment/export?ids={urllib.parse.quote(str(archive_payment_row['id']))}", raw=True)
        assert status_code == 200 and "application/vnd.ms-excel" in content_type and payload.startswith(b"<?xml")
        call("POST", "/finance/archive-settlements/payment/review", {"settlement_ids": [], "approved": True}, expected=(422,))
        call("POST", "/finance/archive-settlements/payment/review", {"settlement_ids": [archive_payment_row["id"]], "approved": False, "comment": ""}, expected=(422,))
        archive_payment_review = call("POST", "/finance/archive-settlements/payment/review", {"settlement_ids": [archive_payment_row["id"]], "approved": True, "comment": "归档费支付审核通过"})
        assert archive_payment_review["reviewed"] == 1 and archive_payment_review["status"] == "已支付"
        archive_payment_decision_id = archive_payment_review["record_ids"][0]
        archive_payment_decision = call("GET", f"/records/{archive_payment_decision_id}")
        assert archive_payment_decision["status"] == "已支付" and archive_payment_decision["data"]["source_application_id"] == paid_application_id
        call("PATCH", f"/records/{archive_payment_decision_id}", {"status": "已拒绝"}, expected=(409,))
        call("POST", f"/records/{archive_payment_decision_id}/transition", {"to_status": "已拒绝", "comment": "绕过"}, expected=(409,))
        call("DELETE", f"/records/{archive_payment_decision_id}", expected=(409,))
        call("POST", "/records", {"module": "finance_archive_settlement", "serial_no": serial("BYPASS-ARCHIVE-PAY"), "title": "绕过归档费支付", "status": "已支付", "owner": USERNAME}, expected=(422,))
        call("POST", "/finance/archive-settlements/payment/review", {"settlement_ids": [archive_payment_row["id"]], "approved": True, "comment": "重复支付"}, expected=(409,))
        assert call("GET", f"/finance/archive-settlements/payment?case_no={urllib.parse.quote(case['serial_no'])}")["total"] == 0
        archive_paid = call("GET", f"/finance/archive-settlements/paid?case_no={urllib.parse.quote(case['serial_no'])}&payment_from={today_text}&payment_to={today_text}")
        assert archive_paid["total"] == 1 and archive_paid["page_size"] == 10
        archive_paid_row = archive_paid["items"][0]
        assert archive_paid_row["id"] == archive_payment_decision_id and archive_paid_row["status"] == "已支付"
        assert archive_paid_row["data"]["archive_payment_reviewer"] == USERNAME
        assert archive_paid_row["data"]["archive_payment_comment"] == "归档费支付审核通过"
        assert archive_paid_row["data"]["archive_no"] == archive_case_payload["archive_no"]
        assert archive_paid["totals"]["receipt_amount"] == 200 and archive_paid["totals"]["archive_fee_amount"] == 16
        call("GET", "/finance/archive-settlements/paid?payment_from=2026-12-31&payment_to=2026-01-01", expected=(422,))
        call("GET", "/finance/archive-settlements/paid/export", expected=(422,))
        status_code, payload, content_type = call("GET", f"/finance/archive-settlements/paid/export?ids={archive_payment_decision_id}", raw=True)
        assert status_code == 200 and "application/vnd.ms-excel" in content_type and payload.startswith(b"<?xml")
        call("POST", "/finance/archive-settlements/paid/rollback", {"record_ids": [], "comment": "回滚"}, expected=(422,))
        call("POST", "/finance/archive-settlements/paid/rollback", {"record_ids": [archive_payment_decision_id], "comment": "   "}, expected=(422,))
        call("POST", "/finance/archive-settlements/paid/rollback", {"record_ids": [paid_application_id], "comment": "错误记录"}, expected=(409,))
        archive_paid_rollback = call("POST", "/finance/archive-settlements/paid/rollback", {"record_ids": [archive_payment_decision_id], "comment": "归档费支付回滚验收"})
        assert archive_paid_rollback["rolled_back"] == 1 and archive_paid_rollback["status"] == "已回滚"
        assert call("GET", f"/finance/archive-settlements/paid?case_no={urllib.parse.quote(case['serial_no'])}")["total"] == 0
        restored_archive_payment = call("GET", f"/finance/archive-settlements/payment?case_no={urllib.parse.quote(case['serial_no'])}")
        assert restored_archive_payment["total"] == 1 and restored_archive_payment["items"][0]["id"] == archive_payment_row["id"]
        assert any(item["action"] == "回滚归档费支付" and item["from_status"] == "已支付" and item["to_status"] == "已回滚" for item in call("GET", f"/records/{archive_payment_decision_id}/history")["items"])
        archive_payment_rereview = call("POST", "/finance/archive-settlements/payment/review", {"settlement_ids": [archive_payment_row["id"]], "approved": True, "comment": "归档费重新支付验收"})
        assert archive_payment_rereview["record_ids"] == [archive_payment_decision_id]
        assert call("GET", f"/finance/archive-settlements/paid?case_no={urllib.parse.quote(case['serial_no'])}")["total"] == 1
        call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [paid_application_id], "action": "rollback", "comment": "归档费仍有效时禁止回退"}, expected=(409,))
        call("POST", "/finance/archive-settlements/paid/rollback", {"record_ids": [archive_payment_decision_id], "comment": "进入拒绝支付验收"})
        archive_payment_rejected = call("POST", "/finance/archive-settlements/payment/review", {"settlement_ids": [archive_payment_row["id"]], "approved": False, "comment": "归档费拒绝支付验收"})
        assert archive_payment_rejected["record_ids"] == [archive_payment_decision_id]
        rejected_query = urllib.parse.urlencode({
            "case_no": case["serial_no"],
            "submitted_by": USERNAME,
            "reviewer": USERNAME,
            "submitted_from": today_text,
            "submitted_to": today_text,
            "reviewed_from": today_text,
            "reviewed_to": today_text,
        })
        archive_rejected = call("GET", f"/finance/archive-settlements/rejected?{rejected_query}")
        assert archive_rejected["total"] == 1 and archive_rejected["page_size"] == 10
        archive_rejected_row = archive_rejected["items"][0]
        assert archive_rejected_row["id"] == archive_payment_decision_id and archive_rejected_row["status"] == "已拒绝"
        assert archive_rejected_row["data"]["archive_payment_reviewer"] == USERNAME
        assert archive_rejected_row["data"]["archive_payment_comment"] == "归档费拒绝支付验收"
        assert archive_rejected["totals"]["receipt_amount"] == 200 and archive_rejected["totals"]["archive_fee_amount"] == 16
        call("GET", "/finance/archive-settlements/rejected?reviewed_from=2026-12-31&reviewed_to=2026-01-01", expected=(422,))
        call("GET", "/finance/archive-settlements/rejected/export", expected=(422,))
        call("GET", "/finance/archive-settlements/rejected/export?ids=invalid", expected=(422,))
        status_code, payload, content_type = call("GET", f"/finance/archive-settlements/rejected/export?ids={archive_payment_decision_id}", raw=True)
        assert status_code == 200 and "application/vnd.ms-excel" in content_type and payload.startswith(b"<?xml")
        call("POST", "/finance/archive-settlements/rejected/rollback", {"record_ids": [], "comment": "回滚"}, expected=(422,))
        call("POST", "/finance/archive-settlements/rejected/rollback", {"record_ids": [archive_payment_decision_id], "comment": "   "}, expected=(422,))
        call("POST", "/finance/archive-settlements/rejected/rollback", {"record_ids": [paid_application_id], "comment": "错误记录"}, expected=(409,))
        rejected_rollback = call("POST", "/finance/archive-settlements/rejected/rollback", {"record_ids": [archive_payment_decision_id], "comment": "拒绝记录回滚验收"})
        assert rejected_rollback["rolled_back"] == 1 and rejected_rollback["status"] == "已支付"
        assert call("GET", f"/finance/archive-settlements/rejected?case_no={urllib.parse.quote(case['serial_no'])}")["total"] == 0
        assert call("GET", f"/finance/archive-settlements/paid?case_no={urllib.parse.quote(case['serial_no'])}")["total"] == 1
        assert any(item["action"] == "回滚归档费拒绝" and item["from_status"] == "已拒绝" and item["to_status"] == "已支付" for item in call("GET", f"/records/{archive_payment_decision_id}/history")["items"])
        call("POST", "/finance/archive-settlements/paid/rollback", {"record_ids": [archive_payment_decision_id], "comment": "再次进入拒绝验收"})
        second_rejection = call("POST", "/finance/archive-settlements/payment/review", {"settlement_ids": [archive_payment_row["id"]], "approved": False, "comment": "重新申请前拒绝"})
        assert second_rejection["record_ids"] == [archive_payment_decision_id]
        call("POST", "/finance/archive-settlements/rejected/reapply", {"record_ids": [], "comment": ""}, expected=(422,))
        call("POST", "/finance/archive-settlements/rejected/reapply", {"record_ids": [archive_payment_decision_id, archive_payment_decision_id], "comment": ""}, expected=(422,))
        call("POST", "/finance/archive-settlements/rejected/reapply", {"record_ids": [paid_application_id], "comment": "错误记录"}, expected=(409,))
        rejected_reapply = call("POST", "/finance/archive-settlements/rejected/reapply", {"record_ids": [archive_payment_decision_id], "comment": ""})
        assert rejected_reapply["reapplied"] == 1 and rejected_reapply["status"] == "待支付"
        assert call("GET", f"/finance/archive-settlements/rejected?case_no={urllib.parse.quote(case['serial_no'])}")["total"] == 0
        reapplied_payment = call("GET", f"/finance/archive-settlements/payment?case_no={urllib.parse.quote(case['serial_no'])}")
        assert reapplied_payment["total"] == 1 and reapplied_payment["items"][0]["id"] == archive_payment_row["id"]
        assert any(item["action"] == "重新申请归档费" and item["from_status"] == "已拒绝" and item["to_status"] == "已回滚" for item in call("GET", f"/records/{archive_payment_decision_id}/history")["items"])
        call("POST", "/finance/archive-settlements/rejected/reapply", {"record_ids": [archive_payment_decision_id], "comment": "重复重新申请"}, expected=(409,))
        final_archive_payment = call("POST", "/finance/archive-settlements/payment/review", {"settlement_ids": [archive_payment_row["id"]], "approved": True, "comment": "重新申请后支付"})
        assert final_archive_payment["record_ids"] == [archive_payment_decision_id]
        outside_paid_list = call("GET", f"/finance/general-settlements/applications?case_no={urllib.parse.quote(case['serial_no'])}&status={urllib.parse.quote('已付款')}&paid_to=2000-01-01")
        assert paid_application_id not in {item["id"] for item in outside_paid_list["items"]}
        call("GET", f"/finance/general-settlements/applications?status={urllib.parse.quote('已付款')}&paid_from=2026-12-31&paid_to=2026-01-01", expected=(422,))
        for export_kind in ["settlement", "receipt", "case"]:
            status_code, payload, content_type = call("GET", f"/finance/general-settlements/export?kind={export_kind}&application_ids={paid_application_id}", raw=True)
            assert status_code == 200 and "application/vnd.ms-excel" in content_type and payload.startswith(b"<?xml")
        call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [paid_application_id], "action": "paid"}, expected=(409,))
        call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [paid_application_id], "action": "rollback", "comment": ""}, expected=(422,))
        call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [paid_application_id], "action": "rollback", "comment": "归档费已支付时仍禁止回退"}, expected=(409,))
        call("POST", "/finance/archive-settlements/paid/rollback", {"record_ids": [archive_payment_decision_id], "comment": "释放源结算回退"})
        paid_rollback = call("POST", "/finance/general-settlements/applications/payment", {"application_ids": [paid_application_id], "action": "rollback", "comment": "已付款结算回退验收"})
        assert paid_rollback["processed"] == 1 and paid_rollback["status"] == "已退回"
        paid_rollback_record = call("GET", f"/records/{paid_application_id}")
        assert paid_rollback_record["status"] == "已退回" and paid_rollback_record["data"]["rollback_comment"] == "已付款结算回退验收"
        assert any(item["action"] == "回退结算" and item["from_status"] == "已付款" and item["to_status"] == "已退回" for item in call("GET", f"/records/{paid_application_id}/history")["items"])
        paid_after_rollback = call("GET", f"/finance/general-settlements/applications?case_no={urllib.parse.quote(case['serial_no'])}&status={urllib.parse.quote('已付款')}")
        assert paid_application_id not in {item["id"] for item in paid_after_rollback["items"]}
        assert call("GET", f"/finance/archive-settlements/pending?case_no={urllib.parse.quote(case['serial_no'])}")["total"] == 0
        restored_after_paid_rollback = call("GET", f"/finance/general-settlements/pending?case_no={urllib.parse.quote(case['serial_no'])}")
        assert incoming["id"] in {item["id"] for item in restored_after_paid_rollback["items"]}
        call("DELETE", f"/finance/general-settlements/applications/{paid_application_id}", expected=(204,))
        settlement_applications.remove(paid_application_id)
        call("GET", f"/records/{archive_payment_decision_id}", expected=(404,))
        passed("结算管理待结算候选、金额公式、三类Excel、原子申请、待审核、待付款、已付款及已拒绝列表、归档费待归档/待支付/已支付/已拒绝列表与导出、归档费拒绝回滚与重新申请、支付审核与回滚重审、源结算生命周期拦截、付款日期筛选、待付款/已付款回退、重新申请、标记支付和通用接口防绕过")

        incomplete_fee = call("POST", "/finance/fees", {"title": "冒烟三要素缺失费用", "amount": 10, "fee_type": "官方费用", "case_no": "", "handler": USERNAME, "court": "测试法院", "document_no": "SMOKE-MISSING"}, expected=(201,))
        records.append(incomplete_fee["id"])
        assert incomplete_fee["data"]["expense_scope"] == "" and incomplete_fee["data"]["expense_subtype"] == ""
        readiness = call("GET", f"/finance/fees/{incomplete_fee['id']}/readiness")
        assert readiness["ready"] is False and any("关联案件" in item for item in readiness["missing"])
        call("POST", f"/finance/fees/{incomplete_fee['id']}/submit", {"comment": "三要素应拦截"}, expected=(422,))
        law_official_fee = call("POST", "/finance/fees", {"title": "SMOKE律所官费", "amount": 12, "fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "官费", "handler": USERNAME}, expected=(201,))
        platform_third_party_fee = call("POST", "/finance/fees", {"title": "SMOKE平台第三方费用", "amount": 13, "fee_type": "其他费用", "expense_scope": "平台", "expense_subtype": "第三方费用", "handler": USERNAME}, expected=(201,))
        internal_scoped_fee = call("POST", "/finance/fees", {"title": "SMOKE内部分类费用", "amount": 14, "fee_type": "内部费用", "expense_scope": "内部", "expense_subtype": "内部费用", "handler": USERNAME}, expected=(201,))
        records.extend([law_official_fee["id"], platform_third_party_fee["id"], internal_scoped_fee["id"]])
        assert law_official_fee["data"]["expense_scope"] == "律所" and law_official_fee["data"]["expense_subtype"] == "官费"
        assert platform_third_party_fee["data"]["expense_scope"] == "平台" and platform_third_party_fee["data"]["expense_subtype"] == "第三方费用"
        assert internal_scoped_fee["data"]["expense_scope"] == "内部" and internal_scoped_fee["data"]["expense_subtype"] == "内部费用"
        call("POST", "/finance/fees", {"title": "费用归属冲突", "amount": 1, "fee_type": "官方费用", "expense_scope": "内部", "expense_subtype": "官费", "handler": USERNAME}, expected=(422,))
        call("POST", "/finance/fees", {"title": "费用子类型冲突", "amount": 1, "fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "代理费", "handler": USERNAME}, expected=(422,))
        internal_credit = call("POST", "/finance/fees", {"title": "冒烟内部负数冲销", "amount": -100.001, "fee_type": "内部费用", "case_no": case["serial_no"], "handler": USERNAME}, expected=(201,))
        records.append(internal_credit["id"])
        assert internal_credit["data"]["amount"] == -100.01 and internal_credit["data"]["is_refund"] is True
        agency_fee = call("POST", "/finance/fees", {"title": "SMOKE代理费", "amount": 20, "fee_type": "代理费", "case_no": case["serial_no"], "handler": USERNAME}, expected=(201,))
        other_fee = call("POST", "/finance/fees", {"title": "SMOKE其他费用", "amount": 30, "fee_type": "其他费用", "case_no": case["serial_no"], "handler": USERNAME}, expected=(201,))
        records.extend([agency_fee["id"], other_fee["id"]])
        assert agency_fee["data"]["fee_type"] == "代理费" and other_fee["data"]["fee_type"] == "其他费用"
        rejected_commission = call("POST", "/finance/fees", {"title": "SMOKE提成拒绝审批", "customer": case["customer"], "amount": 88, "fee_type": "内部费用", "case_no": case["serial_no"], "case_record_id": case["id"], "handler": USERNAME, "payee": "冒烟提成对象"}, expected=(201,))
        records.append(rejected_commission["id"])
        call("POST", f"/finance/fees/{rejected_commission['id']}/submit", {"comment": "提交提成审批"})
        call("POST", f"/finance/fees/{internal_credit['id']}/submit", {"comment": "提交内部提成退费审批"})
        refund_candidates = call("GET", "/finance/fees/refund-review-candidates")
        refund_candidate_ids = {item["id"] for item in refund_candidates["items"]}
        assert internal_credit["id"] in refund_candidate_ids and rejected_commission["id"] not in refund_candidate_ids and agency_fee["id"] not in refund_candidate_ids
        internal_credit = call("POST", f"/finance/fees/{internal_credit['id']}/review", {"approved": False, "comment": "退费资料退回"})
        assert internal_credit["status"] == "已驳回"
        assert any(item["action"] == "内部提成退费审批驳回" for item in call("GET", f"/records/{internal_credit['id']}/history")["items"])
        rejected_commission = call("POST", f"/finance/fees/{rejected_commission['id']}/review", {"approved": False, "comment": "提成资料退回"})
        assert rejected_commission["status"] == "已驳回"
        call("POST", f"/finance/fees/{rejected_commission['id']}/review", {"approved": False}, expected=(409,))
        assert any(item["action"] == "费用审批驳回" for item in call("GET", f"/records/{rejected_commission['id']}/history")["items"])
        voided_commission = call("POST", f"/finance/fees/{rejected_commission['id']}/void", {"comment": "已拒绝请款单作废验收"})
        assert voided_commission["status"] == "已作废" and voided_commission["data"]["voided_by"] == USERNAME
        call("POST", f"/finance/fees/{rejected_commission['id']}/void", {"comment": "重复作废应拦截"}, expected=(409,))
        call("POST", f"/finance/fees/{agency_fee['id']}/void", {"comment": "非内部费用应拦截"}, expected=(409,))
        assert any(item["action"] == "请款单作废" for item in call("GET", f"/records/{rejected_commission['id']}/history")["items"])
        batch_commissions = []
        for suffix, amount in [("A", 66), ("B", 77)]:
            batch_fee = call("POST", "/finance/fees", {"title": f"SMOKE批量提成审批{suffix}", "customer": case["customer"], "amount": amount, "fee_type": "内部费用", "case_no": case["serial_no"], "case_record_id": case["id"], "handler": USERNAME, "payee": "冒烟提成对象"}, expected=(201,))
            records.append(batch_fee["id"]); batch_commissions.append(batch_fee)
            call("POST", f"/finance/fees/{batch_fee['id']}/submit", {"comment": "提交批量提成审批"})
        call("POST", "/finance/fees/batch-review", {"fee_ids": [], "approved": True}, expected=(422,))
        batch_review = call("POST", "/finance/fees/batch-review", {"fee_ids": [item["id"] for item in batch_commissions], "approved": True, "comment": "批量提成审批通过"})
        assert batch_review["reviewed"] == 2 and batch_review["status"] == "已审批"
        call("POST", "/finance/fees/batch-review", {"fee_ids": [batch_commissions[0]["id"]], "approved": True}, expected=(409,))
        batch_detail_types = ",".join(item["title"] for item in batch_commissions)
        internal_detail_query = urllib.parse.urlencode({"scope": "company", "case_no": case["serial_no"], "payee": "冒烟提成对象", "fee_types": batch_detail_types})
        internal_detail = call("GET", f"/finance/internal-fees?{internal_detail_query}")
        internal_detail_ids = {item["id"] for item in internal_detail["items"]}
        expected_internal_detail_ids = {item["id"] for item in batch_commissions}
        assert internal_detail_ids == expected_internal_detail_ids, (internal_detail_ids, expected_internal_detail_ids, internal_detail)
        assert internal_detail["total"] == 2 and internal_detail["total_amount"] == 143
        assert all(item["data"]["payment_status"] == "未付" for item in internal_detail["items"])
        internal_detail_page = call("GET", f"/finance/internal-fees?{internal_detail_query}&page_size=1")
        assert internal_detail_page["total"] == 2 and len(internal_detail_page["items"]) == 1 and internal_detail_page["page_size"] == 1
        personal_detail_query = urllib.parse.urlencode({"scope": "mine", "case_no": case["serial_no"], "payee": "冒烟提成对象", "fee_types": batch_detail_types})
        assert call("GET", f"/finance/internal-fees?{personal_detail_query}")["total"] == 0
        selected_detail_ids = ",".join(str(item["id"]) for item in batch_commissions)
        export_status, export_payload, export_type = call("GET", f"/finance/internal-fees/export?scope=company&ids={selected_detail_ids}", raw=True)
        assert export_status == 200 and export_type.startswith("application/vnd.ms-excel")
        assert b"Excel.Sheet" in export_payload and b"<Workbook" in export_payload
        call("GET", "/finance/internal-fees/export?scope=company&ids=999999999", expected=(422,))
        other_payee_fee = call("POST", "/finance/fees", {"title": "SMOKE异收款人提成", "customer": case["customer"], "amount": 33, "fee_type": "内部费用", "case_no": case["serial_no"], "case_record_id": case["id"], "handler": USERNAME, "payee": "冒烟其他收款人"}, expected=(201,))
        records.append(other_payee_fee["id"])
        call("POST", f"/finance/fees/{other_payee_fee['id']}/submit", {"comment": "提交异收款人提成"})
        call("POST", f"/finance/fees/{other_payee_fee['id']}/approve", {"comment": "异收款人提成审批通过"})
        call("POST", "/finance/payment-packages/preview", {"fee_ids": []}, expected=(422,))
        call("POST", "/finance/payment-packages/preview", {"fee_ids": [batch_commissions[0]["id"], other_payee_fee["id"]]}, expected=(409,))
        call("POST", "/finance/payment-packages/preview", {"fee_ids": [internal_credit["id"]]}, expected=(409,))
        packages_before = call("GET", "/finance/payment-packages")["total"]
        payment_preview = call("POST", "/finance/payment-packages/preview", {"fee_ids": [item["id"] for item in batch_commissions]})
        assert payment_preview["package_no"].startswith("P") and payment_preview["payee"] == "冒烟提成对象" and payment_preview["total_amount"] == 143 and len(payment_preview["items"]) == 2
        assert call("GET", "/finance/payment-packages")["total"] == packages_before
        payment_package = call("POST", "/finance/payment-packages", {"fee_ids": [item["id"] for item in batch_commissions], "package_no": payment_preview["package_no"], "comment": "内部提成打包付款验收"}, expected=(201,))
        payment_packages.append(payment_package["id"])
        assert payment_package["module"] == "finance_package" and payment_package["status"] == "待核销" and payment_package["data"]["total_amount"] == 143
        call("POST", "/finance/payment-packages", {"fee_ids": [item["id"] for item in batch_commissions], "package_no": payment_preview["package_no"]}, expected=(409,))
        package_rows = call("GET", "/finance/payment-packages")["items"]
        assert any(item["id"] == payment_package["id"] for item in package_rows)
        for packaged_fee in batch_commissions:
            paid_fee = call("GET", f"/records/{packaged_fee['id']}")
            assert paid_fee["status"] == "已付款" and paid_fee["data"]["payment_package_id"] == payment_package["id"] and paid_fee["data"]["payment_package_no"] == payment_preview["package_no"]
            assert any(item["action"] == "打包付款" for item in call("GET", f"/records/{packaged_fee['id']}/history")["items"])
        assert any(item["action"] == "创建付款包" for item in call("GET", f"/records/{payment_package['id']}/history")["items"])
        call("POST", "/records", {"module": "finance_package", "serial_no": serial("FAKE-PACKAGE"), "title": "伪造付款包", "status": "待核销", "owner": USERNAME, "data": {}}, expected=(422,))
        call("PATCH", f"/records/{payment_package['id']}", {"status": "已核销"}, expected=(409,))
        call("POST", f"/records/{payment_package['id']}/transition", {"to_status": "已核销", "comment": "通用流转应拦截"}, expected=(409,))
        call("DELETE", f"/records/{payment_package['id']}", expected=(409,))
        call("POST", f"/finance/payment-packages/{payment_package['id']}/writeoff", {"amount": 143, "paid_date": str(date.today()), "payment_method": "自动扣款", "invoice_no": "   ", "remark": "空单据号应拦截"}, expected=(422,))
        call("POST", f"/finance/payment-packages/{payment_package['id']}/writeoff", {"amount": 143, "paid_date": str(date.today()), "payment_method": "支票", "invoice_no": serial("PACK-VOUCHER")}, expected=(422,))
        call("POST", f"/finance/payment-packages/{payment_package['id']}/writeoff", {"amount": 142, "paid_date": str(date.today()), "payment_method": "自动扣款", "invoice_no": serial("PACK-VOUCHER")}, expected=(409,))
        package_voucher = serial("PACK-VOUCHER")
        written_off_package = call("POST", f"/finance/payment-packages/{payment_package['id']}/writeoff", {"amount": 143, "paid_date": str(date.today()), "payment_method": "自动扣款", "invoice_no": package_voucher, "remark": "付款包核销验收"})
        assert written_off_package["status"] == "已付款" and written_off_package["data"]["payment_status"] == "已付款"
        assert written_off_package["data"]["invoice_no"] == package_voucher and written_off_package["data"]["writeoff_status"] == "已核销"
        package_rows_after_writeoff = call("GET", "/finance/payment-packages")["items"]
        listed_written_off_package = next(item for item in package_rows_after_writeoff if item["id"] == payment_package["id"])
        assert listed_written_off_package["status"] == "已付款"
        assert listed_written_off_package["data"]["invoice_no"] == package_voucher and listed_written_off_package["data"]["remark"] == "付款包核销验收"
        call("POST", f"/finance/payment-packages/{payment_package['id']}/writeoff", {"amount": 143, "paid_date": str(date.today()), "payment_method": "自动扣款", "invoice_no": package_voucher}, expected=(409,))
        assert any(item["action"] == "付款核销" for item in call("GET", f"/records/{payment_package['id']}/history")["items"])
        for packaged_fee in batch_commissions:
            written_off_fee = call("GET", f"/records/{packaged_fee['id']}")
            assert written_off_fee["data"]["writeoff_status"] == "已核销" and written_off_fee["data"]["writeoff_voucher_no"] == package_voucher
            assert any(item["action"] == "付款包核销" for item in call("GET", f"/records/{packaged_fee['id']}/history")["items"])
        call("DELETE", f"/finance/payment-packages/{payment_package['id']}", expected=(409,))
        call("DELETE", f"/finance/payment-packages/{payment_package['id']}?reverse_paid=true", expected=(204,))
        payment_packages.remove(payment_package["id"])
        assert all(item["id"] != payment_package["id"] for item in call("GET", "/finance/payment-packages")["items"])
        for packaged_fee in batch_commissions:
            restored_fee = call("GET", f"/records/{packaged_fee['id']}")
            assert restored_fee["status"] == "已审批" and "payment_package_id" not in restored_fee["data"]
            assert any(item["action"] == "冲正已核销付款包" for item in call("GET", f"/records/{packaged_fee['id']}/history")["items"])
        settlement_fee = call("POST", "/finance/fees", {"title": "SMOKE待结算内部提成", "customer": case["customer"], "amount": 120, "fee_type": "内部费用", "case_no": case["serial_no"], "case_record_id": case["id"], "handler": USERNAME, "payee": "冒烟回款单位"}, expected=(201,))
        records.append(settlement_fee["id"])
        call("POST", f"/finance/fees/{settlement_fee['id']}/submit", {"comment": "提交内部费用"})
        call("POST", f"/finance/fees/{settlement_fee['id']}/approve", {"comment": "内部费用审批通过"})
        settlement_tx = call("POST", "/finance/transactions", {"finance_record_id": settlement_fee["id"], "transaction_type": "付款", "amount": 120, "transaction_date": str(date.today()), "voucher_no": serial("SMOKE-SETTLEMENT-PAY")}, expected=(201,))
        transactions.append(settlement_tx["id"])
        pending_settlements = call("GET", "/finance/settlements/pending")
        pending_row = next(item for item in pending_settlements["items"] if item["id"] == settlement_fee["id"])
        assert pending_row["status"] == "已付款" and pending_row["data"]["case_no"] == case["serial_no"] and pending_row["data"]["settlement_status"] == "已付款"
        call("POST", "/finance/settlements/mark-commission-paid", {"fee_ids": []}, expected=(422,))
        marked_settlement = call("POST", "/finance/settlements/mark-commission-paid", {"fee_ids": [settlement_fee["id"]], "comment": "内部提成发放验收"})
        assert marked_settlement["marked"] == 1 and settlement_fee["id"] not in {item["id"] for item in call("GET", "/finance/settlements/pending")["items"]}
        call("POST", "/finance/settlements/mark-commission-paid", {"fee_ids": [settlement_fee["id"]]}, expected=(409,))
        assert any(item["action"] == "标识提成已发" for item in call("GET", f"/records/{settlement_fee['id']}/history")["items"])
        call("POST", "/finance/fees", {"title": "冒烟非法负数官费", "amount": -1, "fee_type": "官方费用", "case_no": case["serial_no"], "handler": USERNAME}, expected=(422,))
        fee = call("POST", "/finance/fees", {"title": "冒烟官方费用", "customer": "冒烟客户", "amount": 1000, "fee_type": "官方费用", "case_no": case["serial_no"], "case_record_id": case["id"], "contract_record_id": contract["id"], "handler": USERNAME, "court": "上海市测试人民法院", "document_no": "SMOKE-NOTICE", "payee": "测试法院"}, expected=(201,))
        records.append(fee["id"])
        assert fee["data"]["case_id"] == case["id"] and fee["data"]["contract_id"] == contract["id"] and fee["data"]["contract_no"] == contract["serial_no"]
        assert call("GET", f"/finance/fees/{fee['id']}/readiness")["ready"] is True
        call("POST", f"/finance/fees/{fee['id']}/submit", {"comment": "提交"})
        call("POST", f"/finance/fees/{fee['id']}/approve", {"comment": "通过"})
        tx1 = call("POST", "/finance/transactions", {"finance_record_id": fee["id"], "transaction_type": "付款", "amount": 400, "transaction_date": str(date.today()), "voucher_no": "SMOKE-PAY-1"}, expected=(201,))
        transactions.append(tx1["id"])
        call("POST", f"/finance/fees/{fee['id']}/writeoff", {"voucher_no": serial("HX-EARLY"), "comment": "付款未完成应拦截"}, expected=(409,))
        call("POST", "/finance/transactions", {"finance_record_id": fee["id"], "transaction_type": "付款", "amount": 700, "transaction_date": str(date.today())}, expected=(409,))
        tx2 = call("POST", "/finance/transactions", {"finance_record_id": fee["id"], "transaction_type": "付款", "amount": 600, "transaction_date": str(date.today()), "voucher_no": "SMOKE-PAY-2"}, expected=(201,))
        transactions.append(tx2["id"])
        writeoff = call("POST", f"/finance/fees/{fee['id']}/writeoff", {"voucher_no": serial("HX"), "comment": "付款凭证核对无误"})
        assert writeoff["data"]["writeoff_status"] == "已核销" and writeoff["data"]["written_off_by"] == USERNAME
        call("POST", f"/finance/fees/{fee['id']}/writeoff", {"voucher_no": serial("HX-DUP"), "comment": "重复核销应拦截"}, expected=(409,))
        history = call("GET", f"/records/{fee['id']}/history")
        assert any(item["action"] == "付款核销" for item in history["items"])
        fee_query_params = urllib.parse.urlencode({
            "case_no": case["serial_no"],
            "customer": "冒烟客户",
            "paid_organization": "测试法院",
            "payment_status": "已付款",
            "paid_from": str(date.today()),
            "paid_to": str(date.today()),
            "fee_types": "官方费用",
            "page": 1,
            "page_size": 1,
        })
        fee_query = call("GET", f"/finance/fees/query?{fee_query_params}")
        assert fee_query["total"] == 1 and fee_query["page"] == 1 and fee_query["page_size"] == 1
        assert len(fee_query["items"]) == 1 and fee_query["items"][0]["id"] == fee["id"]
        fee_query_data = fee_query["items"][0]["data"]
        assert fee_query_data["amount"] == 1000 and fee_query_data["paid_amount"] == 1000
        assert fee_query_data["paid_date"] == str(date.today()) and fee_query_data["payment_status"] == "已付款"
        assert fee_query["totals"]["amount"] == 1000 and fee_query["totals"]["paid_amount"] == 1000
        call("GET", "/finance/fees/query?refund_amount_from=2&refund_amount_to=1", expected=(422,))
        call("GET", "/finance/fees/query?paid_from=2026-07-16&paid_to=2026-07-15", expected=(422,))
        selected_fee_query_export = urllib.parse.urlencode({"selected_only": "true", "ids": fee["id"]})
        export_status, export_payload, export_type = call("GET", f"/finance/fees/query/export?{selected_fee_query_export}", raw=True)
        assert export_status == 200 and export_type.startswith("application/vnd.ms-excel")
        assert b"Excel.Sheet" in export_payload and b"<Workbook" in export_payload and case["serial_no"].encode() in export_payload
        call("GET", "/finance/fees/query/export?selected_only=true", expected=(422,))
        call("GET", "/finance/fees/query/export?selected_only=true&ids=999999999", expected=(422,))

        permission_fee_amount = 98765.43
        permission_fee = call("POST", "/finance/fees", {
            "title": f"SMOKE费用查询金额权限-{suffix}",
            "customer": f"SMOKE费用查询权限客户-{suffix}",
            "amount": permission_fee_amount,
            "fee_type": "内部费用",
            "case_no": case["serial_no"],
            "case_record_id": case["id"],
            "handler": member_name,
            "payee": f"SMOKE权限收款人-{suffix}",
        }, expected=(201,))
        records.append(permission_fee["id"])
        admin_token = TOKEN
        try:
            TOKEN = login(member_name, "SmokePass2026!")["access_token"]
            permission_query_params = urllib.parse.urlencode({"customer": permission_fee["customer"], "page_size": 1})
            permission_query = call("GET", f"/finance/fees/query?{permission_query_params}")
            assert permission_query["total"] == 1 and permission_query["items"][0]["id"] == permission_fee["id"]
            assert permission_query["items"][0]["data"]["amount"] is None
            assert all(value is None for value in permission_query["totals"].values())
            permission_export_query = urllib.parse.urlencode({"selected_only": "true", "ids": permission_fee["id"]})
            permission_export_status, permission_export_payload, permission_export_type = call("GET", f"/finance/fees/query/export?{permission_export_query}", raw=True)
            assert permission_export_status == 200 and permission_export_type.startswith("application/vnd.ms-excel")
            assert str(permission_fee_amount).encode() not in permission_export_payload
        finally:
            TOKEN = admin_token
        passed("费用查询服务端筛选/分页/金额合计、日期与金额边界、选中Excel导出及字段金额权限")
        voucher = multipart_upload("/attachments", {"finance_transaction_id": tx2["id"], "category": "付款凭证", "remark": "冒烟凭证"}, "smoke-voucher.txt", b"sunhold smoke voucher")
        attachments.append(voucher["id"])
        assert call("GET", f"/attachments/{voucher['id']}/download", raw=True)[1]
        batch = call("POST", "/finance/reconciliations", {"period_type": "周对账", "date_from": str(date.today()), "date_to": str(date.today()), "discrepancy_amount": 0, "remark": suffix}, expected=(201,))
        reconciliations.append(batch["id"])
        confirmed = call("POST", f"/finance/reconciliations/{batch['id']}/confirm", {"comment": "核对完成"})
        assert confirmed["status"] == "已确认"
        TOKEN = login(manager_name, "SmokePass2026!")["access_token"]
        assert all(item["id"] != batch["id"] for item in call("GET", "/finance/reconciliations")["items"])
        TOKEN = admin_token
        passed("银行到账认领分配、合同应收同步、付款三要素、负数冲销、内部提成拒绝/作废/打包付款及待结算/标识已发、凭证和对账")

        invoice_case_fee = call("POST", "/finance/fees", {"title": "律师代理费", "customer": case["customer"], "amount": 320.5, "fee_type": "代理费", "case_no": case["serial_no"], "case_record_id": case["id"], "contract_record_id": contract["id"], "handler": USERNAME, "payee": "冒烟收款单位"}, expected=(201,))
        records.append(invoice_case_fee["id"])
        unissued_case_fee = call("POST", "/finance/fees", {"title": "律师代理费", "customer": case["customer"], "amount": 410, "fee_type": "代理费", "case_no": case["serial_no"], "case_record_id": case["id"], "contract_record_id": contract["id"], "handler": USERNAME, "payee": "冒烟收款单位"}, expected=(201,))
        records.append(unissued_case_fee["id"])
        company_only_case_fee = call("POST", "/finance/fees", {"title": "律师代理费", "customer": case["customer"], "amount": 275, "fee_type": "代理费", "case_no": case["serial_no"], "case_record_id": case["id"], "contract_record_id": contract["id"], "handler": manager_name, "payee": "冒烟收款单位"}, expected=(201,))
        records.append(company_only_case_fee["id"])
        before_issue_query = urllib.parse.urlencode({"scope": "company", "case_no": case["serial_no"], "invoice_status": "未开票", "fee_types": "律师代理费", "paid_organization": "冒烟收款单位"})
        before_issue = call("GET", f"/finance/case-fees/invoice-status?{before_issue_query}")
        assert {invoice_case_fee["id"], unissued_case_fee["id"], company_only_case_fee["id"]}.issubset({item["id"] for item in before_issue["items"]})
        invoice = call("POST", "/finance/invoices", {"customer": case["customer"], "case_no": case["serial_no"], "case_record_id": case["id"], "contract_record_id": contract["id"], "case_fee_ids": [invoice_case_fee["id"]], "amount": 320.5, "extra_amount": 12.5, "invoice_title": "冒烟客户有限公司", "taxpayer_id": "91310000INVOICE", "invoice_phone": "021-12345678", "bank_account": "3100000000001", "bank_name": "冒烟测试银行", "invoice_address": "上海市冒烟测试路1号", "invoice_type": "电子普通发票", "invoice_content": "法律服务费", "delivery_method": "电子发票", "email": "invoice@example.com", "remark": suffix}, expected=(201,))
        records.append(invoice["id"])
        assert invoice["data"]["case_id"] == case["id"] and invoice["data"]["contract_id"] == contract["id"] and invoice["data"]["contract_no"] == contract["serial_no"]
        assert invoice["data"]["case_fee_ids"] == [invoice_case_fee["id"]]
        invoice_query = urllib.parse.urlencode({"scope": "mine", "application_no": invoice["serial_no"], "invoice_type": "普票"})
        invoice_list = call("GET", f"/finance/invoices?{invoice_query}")
        assert invoice_list["total"] == 1 and invoice_list["items"][0]["id"] == invoice["id"]
        assert invoice_list["total_amount"] == 320.5 and invoice_list["total_extra_amount"] == 12.5
        assert invoice_list["items"][0]["data"]["invoice_type_display"] == "普票"
        assert call("GET", f"/finance/invoices?{invoice_query}&page_size=1")["page_size"] == 1
        invoice_export = call("GET", f"/finance/invoices/export?scope=mine&ids={invoice['id']}", raw=True)
        assert invoice_export[2].startswith("application/vnd.ms-excel") and b"Excel.Sheet" in invoice_export[1]
        call("GET", "/finance/invoices/export?scope=mine&ids=999999999", expected=(422,))
        withdraw_invoice = call("POST", "/finance/invoices", {"customer": case["customer"], "case_no": case["serial_no"], "case_record_id": case["id"], "amount": 99.9, "invoice_title": "冒烟撤回发票有限公司", "taxpayer_id": "91310000WITHDRAW", "invoice_type": "增值税专用发票", "invoice_content": "律师费", "delivery_method": "电子发票", "email": "withdraw@example.com", "remark": suffix}, expected=(201,))
        records.append(withdraw_invoice["id"])
        call("POST", f"/finance/invoices/{withdraw_invoice['id']}/submit", {"comment": "提交后撤回"})
        withdraw_invoice = call("POST", f"/finance/invoices/{withdraw_invoice['id']}/withdraw", {"comment": "申请人主动撤回"})
        assert withdraw_invoice["status"] == "已撤回" and withdraw_invoice["data"]["withdraw_comment"] == "申请人主动撤回"
        call("POST", f"/finance/invoices/{withdraw_invoice['id']}/withdraw", {"comment": "重复撤回"}, expected=(409,))
        call("POST", f"/records/{withdraw_invoice['id']}/transition", {"to_status": "待审批", "comment": "绕过专用入口"}, expected=(409,))
        assert any(item["action"] == "撤回发票申请" for item in call("GET", f"/records/{withdraw_invoice['id']}/history")["items"])
        withdrawn_query = urllib.parse.urlencode({"scope": "mine", "application_no": withdraw_invoice["serial_no"], "invoice_type": "专票", "invoice_status": "已撤回"})
        withdrawn_list = call("GET", f"/finance/invoices?{withdrawn_query}")
        assert withdrawn_list["total"] == 1 and withdrawn_list["total_amount"] == 0
        call("POST", f"/finance/invoices/{invoice['id']}/issue", {"invoice_no": serial("INV-EARLY"), "invoice_date": str(date.today())}, expected=(409,))
        call("POST", f"/finance/invoices/{invoice['id']}/submit", {"comment": "提交发票申请"})
        call("POST", f"/finance/invoices/{invoice['id']}/review", {"approved": True, "comment": "发票审批通过"})
        pending_query = urllib.parse.urlencode({"scope": "pending", "application_no": invoice["serial_no"], "applicant": "管理者"})
        pending_invoice = call("GET", f"/finance/invoices?{pending_query}")
        assert pending_invoice["total"] == 1 and pending_invoice["items"][0]["status"] == "待开票"
        assert pending_invoice["total_amount"] == 320.5 and pending_invoice["total_extra_amount"] == 12.5
        pending_export = call("GET", f"/finance/invoices/export?scope=pending&ids={invoice['id']}", raw=True)
        assert pending_export[2].startswith("application/vnd.ms-excel") and "待处理开票".encode() in pending_export[1]
        issued = call("POST", f"/finance/invoices/{invoice['id']}/issue", {"invoice_no": serial("INVOICE-NO"), "invoice_date": str(date.today()), "invoice_holder": "冒烟领票人", "extra_amount": 12.5, "comment": "开票完成"})
        assert issued["status"] == "已开票" and issued["data"]["invoice_transaction_id"]
        assert issued["data"]["recipient"] == "冒烟领票人" and issued["data"]["extra_amount"] == 12.5 and issued["data"]["invoiced_opinion"] == "开票完成"
        assert call("GET", f"/finance/invoices?{pending_query}")["total"] == 0
        transactions.append(issued["data"]["invoice_transaction_id"])
        issued_fee_query = urllib.parse.urlencode({"scope": "company", "case_no": case["serial_no"], "invoice_status": "已开票", "fee_types": "律师代理费", "invoice_amount_from": 320.5, "invoice_amount_to": 320.5})
        issued_fee_page = call("GET", f"/finance/case-fees/invoice-status?{issued_fee_query}&page_size=1")
        assert issued_fee_page["total"] == 1 and issued_fee_page["page_size"] == 1
        issued_fee_row = issued_fee_page["items"][0]
        assert issued_fee_row["id"] == invoice_case_fee["id"] and issued_fee_row["data"]["invoice_amount"] == 320.5
        assert issued_fee_row["data"]["invoice_no"] == issued["data"]["invoice_no"] and issued_fee_row["data"]["invoice_record_id"] == invoice["id"]
        assert issued_fee_page["totals"]["amount"] == 320.5 and issued_fee_page["totals"]["invoice_amount"] == 320.5
        still_unissued = call("GET", f"/finance/case-fees/invoice-status?{before_issue_query}")
        still_unissued_ids = {item["id"] for item in still_unissued["items"]}
        assert {unissued_case_fee["id"], company_only_case_fee["id"]}.issubset(still_unissued_ids)
        assert invoice_case_fee["id"] not in still_unissued_ids
        assert still_unissued["totals"]["amount"] == 685 and still_unissued["totals"]["invoice_amount"] == 0, still_unissued
        personal_unissued_query = urllib.parse.urlencode({"scope": "mine", "case_no": case["serial_no"], "invoice_status": "未开票", "fee_types": "律师代理费", "paid_organization": "冒烟收款单位"})
        personal_unissued = call("GET", f"/finance/case-fees/invoice-status?{personal_unissued_query}")
        assert personal_unissued["total"] == 1 and personal_unissued["items"][0]["id"] == unissued_case_fee["id"]
        unissued_export_query = urllib.parse.urlencode({"scope": "company", "invoice_status": "未开票", "fee_types": "律师代理费", "ids": unissued_case_fee["id"]})
        unissued_export = call("GET", f"/finance/case-fees/invoice-status/export?{unissued_export_query}", raw=True)
        assert unissued_export[2].startswith("application/vnd.ms-excel") and b"Excel.Sheet" in unissued_export[1]
        call("GET", "/finance/case-fees/invoice-status/export?scope=company&ids=999999999", expected=(422,))
        call("GET", "/finance/case-fees/invoice-status?invoice_amount_from=10&invoice_amount_to=1", expected=(422,))
        company_query = urllib.parse.urlencode({"scope": "company", "application_no": invoice["serial_no"], "invoice_status": "已开票", "applicant": "管理者"})
        company_invoice = call("GET", f"/finance/invoices?{company_query}&page_size=1")
        assert company_invoice["total"] == 1 and company_invoice["page_size"] == 1
        assert company_invoice["items"][0]["data"]["applicant"] == "管理者"
        assert company_invoice["total_amount"] == 320.5 and company_invoice["total_extra_amount"] == 12.5
        company_export = call("GET", f"/finance/invoices/export?scope=company&ids={invoice['id']}", raw=True)
        assert company_export[2].startswith("application/vnd.ms-excel") and "公司开票".encode() in company_export[1]
        assert "发票号码".encode() in company_export[1] and "申请人".encode() in company_export[1]
        call("POST", f"/finance/invoices/{invoice['id']}/change-number", {"invoice_no": "   "}, expected=(422,))
        changed_invoice_no = serial("INVOICE-CHANGED")
        changed_number = call("POST", f"/finance/invoices/{invoice['id']}/change-number", {"invoice_no": changed_invoice_no})
        assert changed_number["data"]["invoice_no"] == changed_invoice_no
        changed_application_date = date.today() - timedelta(days=2)
        changed_invoice_date = date.today() - timedelta(days=1)
        changed_dates = call("POST", f"/finance/invoices/{invoice['id']}/change-date", {"application_date": str(changed_application_date), "invoice_date": str(changed_invoice_date)})
        assert changed_dates["data"]["application_date"] == str(changed_application_date)
        assert changed_dates["data"]["invoice_date"] == str(changed_invoice_date)
        changed_tx = next(item for item in call("GET", "/finance/transactions")["items"] if item["id"] == issued["data"]["invoice_transaction_id"])
        assert changed_tx["voucher_no"] == changed_invoice_no and changed_tx["transaction_date"] == str(changed_invoice_date)
        invoice_history = call("GET", f"/records/{invoice['id']}/history")["items"]
        assert any(item["action"] == "修改发票号" for item in invoice_history)
        assert any(item["action"] == "修改发票日期" for item in invoice_history)
        invoice_scan = multipart_upload("/attachments", {"record_id": invoice["id"], "category": "发票扫描件", "remark": "发票扫描件验收"}, "invoice-scan.txt", b"invoice scan smoke")
        attachments.append(invoice_scan["id"])
        voided = call("POST", f"/finance/invoices/{invoice['id']}/void", {"reason": "测试发票信息更正后重新开具"})
        assert voided["status"] == "已作废" and voided["data"]["void_reason"]
        after_void_unissued = call("GET", f"/finance/case-fees/invoice-status?{before_issue_query}")
        assert {invoice_case_fee["id"], unissued_case_fee["id"], company_only_case_fee["id"]}.issubset({item["id"] for item in after_void_unissued["items"]})
        assert call("GET", f"/finance/case-fees/invoice-status?{issued_fee_query}")["total"] == 0
        call("POST", f"/finance/invoices/{invoice['id']}/change-number", {"invoice_no": serial("VOID-NO")}, expected=(409,))
        call("POST", f"/finance/invoices/{invoice['id']}/change-date", {"application_date": str(date.today()), "invoice_date": str(date.today())}, expected=(409,))
        invoice_txs = [item for item in call("GET", "/finance/transactions")["items"] if invoice["serial_no"] in (item.get("remark") or "")]
        for item in invoice_txs:
            if item["id"] not in transactions: transactions.append(item["id"])
        reject_invoice = call("POST", "/finance/invoices", {"customer": case["customer"], "case_no": case["serial_no"], "case_record_id": case["id"], "amount": 66.6, "invoice_title": "冒烟驳回开票有限公司", "taxpayer_id": "91310000REJECT", "invoice_type": "增值税普通发票", "invoice_content": "律师费", "delivery_method": "电子发票", "email": "reject@example.com", "remark": suffix}, expected=(201,))
        records.append(reject_invoice["id"])
        call("POST", f"/finance/invoices/{reject_invoice['id']}/change-number", {"invoice_no": changed_invoice_no}, expected=(409,))
        call("POST", f"/finance/invoices/{reject_invoice['id']}/submit", {"comment": "提交待驳回开票"})
        call("POST", f"/finance/invoices/{reject_invoice['id']}/review", {"approved": True, "comment": "进入待开票"})
        call("POST", f"/finance/invoices/{reject_invoice['id']}/reject-issue", {"comment": "   "}, expected=(422,))
        rejected_invoice = call("POST", f"/finance/invoices/{reject_invoice['id']}/reject-issue", {"comment": "发票资料需补充"})
        assert rejected_invoice["status"] == "已驳回" and rejected_invoice["data"]["invoiced_opinion"] == "发票资料需补充"
        call("POST", f"/finance/invoices/{reject_invoice['id']}/reject-issue", {"comment": "重复驳回"}, expected=(409,))
        assert any(item["action"] == "开票驳回" for item in call("GET", f"/records/{reject_invoice['id']}/history")["items"])

        refund = call("POST", "/finance/refunds", {"customer": case["customer"], "case_no": case["serial_no"], "court": "上海市测试人民法院", "original_payment_no": serial("COURT-PAY"), "amount": 88.8, "applicant": USERNAME, "refund_account_name": "冒烟客户有限公司", "refund_bank": "测试银行上海分行", "refund_account": "6222000012345678", "expected_date": str(date.today() + timedelta(days=10)), "reason": "案件结案诉讼费退费", "remark": suffix}, expected=(201,))
        records.append(refund["id"])
        call("POST", f"/finance/refunds/{refund['id']}/complete", {"actual_date": str(date.today()), "voucher_no": serial("REFUND-EARLY")}, expected=(409,))
        call("POST", f"/finance/refunds/{refund['id']}/submit", {"comment": "提交退款审批"})
        call("POST", f"/finance/refunds/{refund['id']}/review", {"approved": True, "comment": "退款审批通过"})
        completed_refund = call("POST", f"/finance/refunds/{refund['id']}/complete", {"actual_date": str(date.today()), "voucher_no": serial("REFUND-VOUCHER"), "comment": "退款到账"})
        assert completed_refund["status"] == "已退款" and completed_refund["data"]["refund_transaction_id"]
        transactions.append(completed_refund["data"]["refund_transaction_id"])
        refund_voucher = multipart_upload("/attachments", {"record_id": refund["id"], "category": "退费凭证", "remark": "退款凭证验收"}, "refund-voucher.txt", b"refund voucher smoke")
        attachments.append(refund_voucher["id"])
        passed("发票申请审批/开票/扫描件/作废冲销、案件费用未开票/已开票查询导出和诉讼费退款审批/到账/凭证")

        template = call("POST", "/templates", {"name": serial("TPL"), "category": "诉讼文书", "version": "1.0", "description": "冒烟模板", "fields": ["当事人", "事实与理由"]}, expected=(201,))
        templates.append(template["id"])
        updated_template = call("PATCH", f"/templates/{template['id']}", {"version": "1.1", "description": "冒烟模板已编辑", "is_active": False})
        assert updated_template["version"] == "1.1" and updated_template["is_active"] is False
        call("POST", "/agent/documents", {"template_id": template["id"], "title": "停用模板不可生成"}, expected=(404,))
        template = call("PATCH", f"/templates/{template['id']}", {"is_active": True})
        assert template["is_active"] is True
        TOKEN = login(outsider_name, "SmokePass2026!")["access_token"]
        revoked_communication = call("POST", "/communications", {"customer_record_id": shared_record["id"], "contact": "撤权前联系人", "phone": "13800000001", "content": "撤权前负责人沟通日志", "occurred_at": datetime.now().isoformat(timespec="seconds")}, expected=(201,))
        communications.append(revoked_communication["id"])
        revoked_agent = call("POST", "/agent/documents", {"template_id": template["id"], "record_id": shared_record["id"], "title": "冒烟客户撤权智能文档", "instruction": "验证共享与创建人均不能绕过客户权限"}, expected=(201,))
        agents.append(revoked_agent["id"])
        TOKEN = admin_token
        reassigned_shared_record = call("PUT", f"/customers/{shared_record['id']}/managers", {"managers": [manager_name], "comment": "撤销原负责人权限并保留共享只读关系"})
        assert reassigned_shared_record["owner"] == manager_name and reassigned_shared_record["data"]["shared_with"] == [member_name]
        downgraded_creator = call("POST", f"/customers/{shared_record['id']}/share", {"recipients": [outsider_name], "comment": "原负责人降为共享只读接收人"})
        assert set(downgraded_creator["data"]["shared_with"]) == {member_name, outsider_name}
        TOKEN = login(member_name, "SmokePass2026!")["access_token"]
        assert all(item["id"] != revoked_agent["id"] for item in call("GET", "/agent/documents")["items"])
        call("POST", "/agent/documents", {"template_id": template["id"], "record_id": shared_record["id"], "title": "共享人不得创建智能文档"}, expected=(403,))
        call("GET", f"/agent/documents/{revoked_agent['id']}/download", expected=(403,))
        call("POST", f"/agent/documents/{revoked_agent['id']}/retry", expected=(403,))
        call("PATCH", f"/agent/documents/{revoked_agent['id']}", {"content": "共享人不得读取或修改历史全文"}, expected=(403,))
        call("POST", f"/agent/documents/{revoked_agent['id']}/writeback", expected=(403,))
        call("DELETE", f"/agent/documents/{revoked_agent['id']}", expected=(403,))
        TOKEN = login(outsider_name, "SmokePass2026!")["access_token"]
        call("PATCH", f"/communications/{revoked_communication['id']}", {"content": "降为共享后旧操作人不得修改"}, expected=(403,))
        call("DELETE", f"/communications/{revoked_communication['id']}", expected=(403,))
        assert all(item["id"] != revoked_agent["id"] for item in call("GET", "/agent/documents")["items"])
        call("GET", f"/agent/documents/{revoked_agent['id']}/download", expected=(403,))
        call("POST", f"/agent/documents/{revoked_agent['id']}/retry", expected=(403,))
        call("PATCH", f"/agent/documents/{revoked_agent['id']}", {"content": "创建人降为共享后不得修改"}, expected=(403,))
        call("POST", f"/agent/documents/{revoked_agent['id']}/writeback", expected=(403,))
        call("DELETE", f"/agent/documents/{revoked_agent['id']}", expected=(403,))
        TOKEN = admin_token
        document = create_record("document", "已归档", "冒烟收文", {"direction": "收文", "document_date": str(date.today()), "case_no": case["serial_no"], "sender": "上海市测试人民法院"})
        assert document["status"] == "待登记"
        file_item = multipart_upload("/attachments", {"record_id": document["id"], "category": "收文附件", "remark": "冒烟附件"}, "smoke-document.txt", b"sunhold document attachment")
        attachments.append(file_item["id"])
        official_upload = multipart_upload("/documents/official/upload", {"category": "收文附件", "remark": "官文原子上传冒烟"}, "official-smoke.pdf", b"%PDF-1.4\nsmoke official document")
        records.append(official_upload["record"]["id"]); attachments.append(official_upload["attachment"]["id"])
        assert official_upload["record"]["module"] == "document" and official_upload["record"]["data"]["direction"] == "收文"
        assert official_upload["record"]["data"]["import_status"] == "已导入" and official_upload["attachment"]["record_id"] == official_upload["record"]["id"]
        call("PATCH", f"/records/{document['id']}", {"status": "已归档"}, expected=(409,))
        call("POST", f"/records/{document['id']}/transition", {"to_status": "待签收", "comment": "绕过专用入口"}, expected=(409,))
        call("POST", f"/documents/{document['id']}/transition", {"to_status": "已签收", "action_date": str(date.today()), "handler": USERNAME}, expected=(409,))
        registered_document = call("POST", f"/documents/{document['id']}/transition", {"to_status": "待签收", "action_date": str(date.today()), "comment": "完成收文登记"})
        assert registered_document["status"] == "待签收" and registered_document["data"]["registered_at"] == str(date.today())
        call("POST", f"/documents/{document['id']}/transition", {"to_status": "已签收", "action_date": str(date.today()), "handler": ""}, expected=(422,))
        signed_document = call("POST", f"/documents/{document['id']}/transition", {"to_status": "已签收", "action_date": str(date.today()), "handler": USERNAME, "comment": "本人签收"})
        assert signed_document["status"] == "已签收" and signed_document["data"]["signer"] == USERNAME
        call("POST", f"/documents/{document['id']}/transition", {"to_status": "已归档", "action_date": str(date.today())}, expected=(422,))
        archived_document = call("POST", f"/documents/{document['id']}/transition", {"to_status": "已归档", "action_date": str(date.today()), "archive_no": serial("DOC-ARCHIVE"), "archive_location": "冒烟档案柜", "comment": "收文归档"})
        assert archived_document["status"] == "已归档" and archived_document["data"]["archive_location"] == "冒烟档案柜"
        assert len(call("GET", f"/records/{document['id']}/history")["items"]) >= 4
        agent = call("POST", "/agent/documents", {"template_id": template["id"], "record_id": document["id"], "title": "冒烟智能文档", "instruction": "生成测试提纲"}, expected=(201,))
        agents.append(agent["id"])
        edited = call("PATCH", f"/agent/documents/{agent['id']}", {"content": "# 冒烟文档\n自动验收内容"})
        assert edited["status"] == "已编辑"
        call("POST", f"/agent/documents/{agent['id']}/writeback", expected=(409,))
        confirmed = call("POST", f"/agent/documents/{agent['id']}/confirm", {"comment": "律师已逐项核对"})
        assert confirmed["status"] == "已人工确认" and confirmed["confirmed_by"] == USERNAME
        edited_again = call("PATCH", f"/agent/documents/{agent['id']}", {"content": "# 冒烟文档\n人工修订后的自动验收内容"})
        assert edited_again["status"] == "已编辑" and not edited_again["confirmed_by"]
        call("POST", f"/agent/documents/{agent['id']}/writeback", expected=(409,))
        call("POST", f"/agent/documents/{agent['id']}/confirm", {"comment": "修订后重新核对"})
        assert len(call("GET", f"/agent/documents/{agent['id']}/download", raw=True)[1]) > 100
        TOKEN = login(member_name, "SmokePass2026!")["access_token"]
        assert all(item["id"] != agent["id"] for item in call("GET", "/agent/documents")["items"])
        call("GET", f"/agent/documents/{agent['id']}/download", expected=(404,))
        call("PATCH", f"/agent/documents/{agent['id']}", {"content": "越权修改"}, expected=(404,))
        TOKEN = admin_token
        written = call("POST", f"/agent/documents/{agent['id']}/writeback")
        attachments.append(written["attachment_id"])
        call("POST", f"/agent/documents/{agent['id']}/writeback", expected=(409,))
        TOKEN = login(member_name, "SmokePass2026!")["access_token"]
        member_agent = call("POST", "/agent/documents", {"template_id": template["id"], "title": "冒烟成员自有智能文档", "instruction": "验证创建人删除权限"}, expected=(201,))
        call("DELETE", f"/agent/documents/{member_agent['id']}", expected=(204,))
        TOKEN = admin_token
        passed("收发文登记/签收/归档、模板编辑停启、附件及智能文档生成编辑下载回写")

        assets = call("GET", "/seals/assets")["items"]
        required_seal_types = {"合同章", "公章", "所函专用章", "法人章", "发票章", "财务专用章", "财务三排章"}
        available_seal_types = {item["seal_type"] for item in assets if item["status"] == "可用"}
        assert required_seal_types <= available_seal_types, f"合同用印缺少基础印章类型：{sorted(required_seal_types - available_seal_types)}"
        asset = next(item for item in assets if item["status"] == "可用")
        linked_seal = call("GET", f"/records/{sync_linked_seal['id']}")
        assert linked_seal["status"] == "待审批" and linked_seal["data"]["contract_no"] == contract["serial_no"]
        linked_contract = call("GET", f"/records/{contract['id']}")
        assert linked_contract["data"]["seal_application_id"] == linked_seal["id"] and linked_contract["data"]["seal_application_no"] == linked_seal["serial_no"]
        call("POST", f"/contracts/{contract['id']}/seal-application", {"seal_asset_id": asset["id"], "copies": 1, "purpose": "重复用印", "use_date": str(date.today() + timedelta(days=1))}, expected=(409,))
        seal = call("POST", "/seals/applications", {"title": "冒烟用印", "customer": "冒烟客户", "case_no": case["serial_no"], "contract_no": contract["serial_no"], "use_type": "案件用印", "seal_asset_id": asset["id"], "copies": 2, "purpose": "接口验收", "use_date": str(date.today() + timedelta(days=1)), "delivery_method": "现场用印", "document_names": "测试文件"}, expected=(201,))
        records.append(seal["id"])
        assert seal["data"]["contract_no"] == contract["serial_no"] and seal["data"]["use_type"] == "案件用印"
        seal_query = urllib.parse.urlencode({"view": "all", "record_status": "草稿", "contract_no": contract["serial_no"]})
        queried_seals = call("GET", f"/seals/applications?{seal_query}")["items"]
        assert any(item["id"] == seal["id"] for item in queried_seals)
        deletable_seal = call("POST", "/seals/applications", {"title": "冒烟可删除用印草稿", "customer": "冒烟客户", "contract_no": contract["serial_no"], "use_type": "合同用印", "seal_asset_id": asset["id"], "copies": 1, "purpose": "草稿删除验收", "use_date": str(date.today() + timedelta(days=1)), "delivery_method": "现场用印"}, expected=(201,))
        call("DELETE", f"/seals/applications/{deletable_seal['id']}", expected=(204,))
        call("GET", f"/records/{deletable_seal['id']}", expected=(404,))
        call("PATCH", f"/records/{seal['id']}", {"status": "已用印"}, expected=(409,))
        call("POST", f"/records/{seal['id']}/transition", {"to_status": "已用印", "comment": "绕过用印审批"}, expected=(409,))
        call("DELETE", f"/records/{seal['id']}", expected=(409,))
        seal_attachment = multipart_upload("/attachments", {"record_id": seal["id"], "category": "用印文件", "remark": "用印打包下载验收"}, f"smoke-seal-{suffix}.txt", b"seal package download smoke")
        attachments.append(seal_attachment["id"])
        zip_status, zip_payload, zip_content_type = call("POST", "/seals/applications/package-download", {"application_ids": [seal["id"]]}, raw=True)
        assert zip_status == 200 and zip_content_type.startswith("application/zip") and zip_payload.startswith(b"PK")
        call("POST", f"/seals/applications/{seal['id']}/submit", {"comment": "提交"})
        approved_seal = call("POST", f"/seals/applications/{seal['id']}/approve", {"approved": True, "comment": "通过"})
        assert approved_seal["status"] == "待用印" and approved_seal["data"]["approval_comment"] == "通过"
        audited_seals = call("GET", "/seals/applications?view=audit")["items"]
        assert any(item["id"] == seal["id"] and item["status"] == "待用印" for item in audited_seals)
        stamped = call("POST", f"/seals/applications/{seal['id']}/stamp", {"actual_copies": 2, "operator": USERNAME, "archive_no": serial("ARCHIVE"), "comment": "登记"})
        assert stamped["status"] == "已用印"
        archived = call("POST", f"/seals/applications/{seal['id']}/archive", {"comment": "归档"})
        assert archived["status"] == "已归档"
        withdrawn_seal = call("POST", "/seals/applications", {"title": "冒烟撤回用印", "customer": "冒烟客户", "case_no": case["serial_no"], "seal_asset_id": asset["id"], "copies": 1, "purpose": "撤回接口验收", "use_date": str(date.today() + timedelta(days=1)), "delivery_method": "现场用印", "document_names": "撤回测试文件"}, expected=(201,))
        records.append(withdrawn_seal["id"])
        call("POST", f"/seals/applications/{withdrawn_seal['id']}/submit", {"comment": "提交后测试撤回"})
        TOKEN = login(member_name, "SmokePass2026!")["access_token"]
        call("POST", f"/seals/applications/{withdrawn_seal['id']}/withdraw", {"comment": "非申请人越权撤回"}, expected=(404,))
        TOKEN = admin_token
        withdrawn_seal = call("POST", f"/seals/applications/{withdrawn_seal['id']}/withdraw", {"comment": "申请人撤回"})
        assert withdrawn_seal["status"] == "已撤回"
        call("POST", f"/seals/applications/{withdrawn_seal['id']}/withdraw", {"comment": "重复撤回"}, expected=(409,))
        seal_history = call("GET", f"/records/{withdrawn_seal['id']}/history")["items"]
        assert any(event["action"] == "撤回用印申请" and event["to_status"] == "已撤回" for event in seal_history)
        approved_withdrawal = call("POST", "/seals/applications", {"title": "冒烟已审撤回用印", "customer": "冒烟客户", "case_no": case["serial_no"], "seal_asset_id": asset["id"], "copies": 1, "purpose": "已审待用印撤回验收", "use_date": str(date.today() + timedelta(days=1)), "delivery_method": "现场用印", "document_names": "已审撤回测试文件"}, expected=(201,))
        records.append(approved_withdrawal["id"])
        call("POST", f"/seals/applications/{approved_withdrawal['id']}/submit", {"comment": "提交审批"})
        approved_withdrawal = call("POST", f"/seals/applications/{approved_withdrawal['id']}/approve", {"approved": True, "comment": "审批通过后撤回"})
        assert approved_withdrawal["status"] == "待用印"
        approved_withdrawal = call("POST", f"/seals/applications/{approved_withdrawal['id']}/withdraw", {"comment": "用印前撤回"})
        assert approved_withdrawal["status"] == "已撤回"
        refused_seal = call("POST", "/seals/applications", {"title": "冒烟拒绝用印", "customer": "冒烟客户", "case_no": case["serial_no"], "seal_asset_id": asset["id"], "copies": 1, "purpose": "拒绝流转验收", "use_date": str(date.today() + timedelta(days=1)), "delivery_method": "现场用印", "document_names": "拒绝测试文件"}, expected=(201,))
        records.append(refused_seal["id"])
        call("POST", f"/seals/applications/{refused_seal['id']}/submit", {"comment": "提交拒绝测试"})
        refused_seal = call("POST", f"/seals/applications/{refused_seal['id']}/approve", {"approved": False, "comment": "材料不完整"})
        assert refused_seal["status"] == "已拒绝" and refused_seal["data"]["approval_comment"] == "材料不完整"
        audited_seals = call("GET", "/seals/applications?view=audit")["items"]
        assert any(item["id"] == refused_seal["id"] and item["status"] == "已拒绝" for item in audited_seals)
        passed("用印申请、单个 ZIP 打包下载、审批、实际用印、归档及受控撤回")

        for analytics_view, expected_charts in {"brand": 4, "lawyer": 4, "refund": 4, "execution-1": 10, "execution-2": 10, "execution-3": 10}.items():
            analytics = call("GET", f"/reports/analytics?view={analytics_view}")
            assert analytics["source"] == "realtime" and len(analytics["charts"]) == expected_charts
            assert all(isinstance(chart["items"], list) for chart in analytics["charts"])
            exported = call("GET", f"/reports/analytics/export?view={analytics_view}", raw=True)
            assert exported[2].startswith("text/csv") and exported[1].startswith(b"\xef\xbb\xbf")
        call("GET", "/reports/analytics?view=unsupported", expected=(422,))
        call("GET", "/reports/analytics?view=brand&source_from=2026-07-31&source_to=2026-07-01", expected=(422,))
        call("GET", f"/reports/analytics?view=lawyer&group_mode={urllib.parse.quote('无效分组')}", expected=(422,))
        analytics_csv = call("GET", "/reports/analytics/export?view=brand", raw=True)[1]
        assert analytics_csv.startswith(b"\xef\xbb\xbf") and "统计图,分组,数值,单位".encode() in analytics_csv
        report = call("POST", "/reports/generate", {"title": "冒烟经营报表", "report_type": "综合经营报表", "period": str(date.today())[:7], "format": "CSV", "description": suffix}, expected=(201,))
        records.append(report["id"])
        published = call("POST", f"/records/{report['id']}/transition", {"to_status": "已发布", "comment": "发布"})
        assert published["status"] == "已发布"
        assert call("GET", f"/reports/{report['id']}/download", raw=True)[1].startswith(b"\xef\xbb\xbf")
        assert call("GET", f"/search?q={urllib.parse.quote('冒烟')}")["total"] >= 1
        assert call("GET", f"/audit/events?keyword={urllib.parse.quote(suffix)}")["total"] >= 1
        passed("经营报表、全局搜索和审计日志")

        active_department = next(item for item in call("GET", "/hr/departments?active_only=true")["items"] if item["is_active"])
        active_job_role = next(item for item in call("GET", "/hr/job-roles?active_only=true")["items"] if item["is_active"])
        atomic_employee_name = f"atomic_hr_{suffix}".lower()
        atomic_employee = call("POST", "/hr/employees", {"username": atomic_employee_name, "display_name": "原子新建员工", "employee_no": serial("HR-ATOMIC"), "company": "上海申浩律师事务所", "department": active_department["name"], "password": "SmokePass2026!", "role": "manager", "position": active_job_role["name"], "is_active": True, "account_type": "员工账号", "data": {"account_type": "员工账号", "joined_at": str(date.today()), "mobile": "13800000001"}}, expected=(201,))
        users.append(atomic_employee["user"]["id"]); records.append(atomic_employee["employee"]["id"])
        assert atomic_employee["employee"]["owner"] == atomic_employee_name and atomic_employee["user"]["username"] == atomic_employee_name and atomic_employee["user"]["role"] == "user"
        call("POST", "/hr/employees", {"username": atomic_employee_name, "display_name": "重复员工", "employee_no": serial("HR-ATOMIC-2"), "company": "上海申浩律师事务所", "department": active_department["name"], "password": "SmokePass2026!", "role": "user", "position": active_job_role["name"], "is_active": True, "account_type": "员工账号", "data": {"account_type": "员工账号"}}, expected=(409,))
        call("POST", "/hr/employees", {"username": "admin", "display_name": "禁止覆盖管理员", "employee_no": serial("HR-ADMIN"), "company": "上海申浩律师事务所", "department": active_department["name"], "password": "SmokePass2026!", "role": "user", "position": active_job_role["name"], "is_active": True, "account_type": "员工账号", "data": {"account_type": "员工账号"}}, expected=(409,))
        call("DELETE", f"/records/{atomic_employee['employee']['id']}", expected=(409,))
        hr = create_record("hr", "试用", "冒烟员工", {"username": member_name, "position": active_job_role["name"], "phone": "13800000000", "joined_at": str(date.today()), "employment_type": "全职"}, department=active_department["name"], owner=member_name)
        call("PATCH", f"/hr/employees/{hr['id']}", {"username": member_name, "display_name": "冒烟员工已修改", "department": active_department["name"], "role": "user", "position": active_job_role["name"], "is_active": True, "email": "hr-smoke@example.com", "mobile": "13900000000", "office_phone": "021-12340000", "joined_at": str(date.today()), "left_at": str(date.today() - timedelta(days=1)), "data": {}}, expected=(422,))
        updated_hr = call("PATCH", f"/hr/employees/{hr['id']}", {"username": member_name, "display_name": "冒烟员工已修改", "department": active_department["name"], "role": "user", "position": active_job_role["name"], "is_active": True, "email": "hr-smoke@example.com", "mobile": "13900000000", "office_phone": "021-12340000", "joined_at": str(date.today()), "left_at": None, "data": {"employment_type": "全职", "staff_role": "授薪律师", "id_no": f"310101{suffix[-8:]}", "school": "华东政法大学", "lawyer_license_no": f"LAW-{suffix}", "annual_leave": 8}})
        assert updated_hr["employee"]["data"]["school"] == "华东政法大学" and updated_hr["employee"]["data"]["lawyer_license_no"] == f"LAW-{suffix}" and updated_hr["employee"]["data"]["annual_leave"] == 8
        assert updated_hr["employee"]["title"] == "冒烟员工已修改" and updated_hr["user"]["mobile"] == "13900000000"
        assert any(item["action"] == "修改员工资料" for item in call("GET", f"/records/{hr['id']}/history")["items"])
        renamed_atomic_name = f"renamed_hr_{suffix}".lower()
        renamed_atomic = call("PATCH", f"/hr/employees/{atomic_employee['employee']['id']}", {"username": renamed_atomic_name, "display_name": "原子新建员工", "department": active_department["name"], "role": "user", "position": active_job_role["name"], "is_active": True, "email": "", "mobile": "13800000001", "office_phone": "", "joined_at": str(date.today()), "left_at": None, "data": {"joined_at": str(date.today()), "mobile": "13800000001"}})
        assert renamed_atomic["user"]["username"] == renamed_atomic_name
        assert renamed_atomic["employee"]["owner"] == renamed_atomic_name and renamed_atomic["employee"]["data"]["username"] == renamed_atomic_name
        disabled_atomic = call("PATCH", f"/hr/employees/{atomic_employee['employee']['id']}", {"username": renamed_atomic_name, "display_name": "原子新建员工", "department": active_department["name"], "role": "user", "position": active_job_role["name"], "is_active": False, "email": "", "mobile": "13800000001", "office_phone": "", "joined_at": str(date.today()), "left_at": None, "data": {"account_type": "员工账号", "joined_at": str(date.today()), "mobile": "13800000001"}})
        assert disabled_atomic["employee"]["data"]["is_active"] is False and disabled_atomic["user"]["is_active"] is False
        reenabled_atomic = call("PATCH", f"/hr/employees/{atomic_employee['employee']['id']}", {"username": renamed_atomic_name, "display_name": "原子新建员工", "department": active_department["name"], "role": "user", "position": active_job_role["name"], "is_active": True, "email": "", "mobile": "13800000001", "office_phone": "", "joined_at": str(date.today()), "left_at": None, "data": {"account_type": "员工账号", "joined_at": str(date.today()), "mobile": "13800000001"}})
        assert reenabled_atomic["employee"]["data"]["is_active"] is True and reenabled_atomic["user"]["is_active"] is True
        login(atomic_employee_name, "SmokePass2026!", expected=(401,))
        assert login(renamed_atomic_name, "SmokePass2026!")["access_token"]
        leave = call("POST", f"/hr/{hr['id']}/subrecords", {"kind": "leave", "data": {"start_date": str(date.today()), "end_date": str(date.today()), "hours": 8, "leave_type": "年假", "remark": "附属记录验收"}}, expected=(201,))
        assert leave["data"]["hours"] == 8 and leave["kind"] == "leave"
        call("POST", f"/hr/{hr['id']}/subrecords", {"kind": "leave", "data": {"start_date": str(date.today()), "end_date": str(date.today() - timedelta(days=1)), "hours": 8, "leave_type": "年假"}}, expected=(422,))
        matter = call("POST", f"/hr/{hr['id']}/subrecords", {"kind": "matter", "data": {"content": "完成入职材料核验", "operation_date": str(date.today())}}, expected=(201,))
        matter = call("PATCH", f"/hr/{hr['id']}/subrecords/{matter['id']}", {"data": {"content": "完成入职材料与权限核验", "operation_date": str(date.today())}})
        assert "权限" in matter["data"]["content"]
        commission = call("POST", f"/hr/{hr['id']}/subrecords", {"kind": "commission", "data": {"start_date": str(date.today()), "end_date": "", "base_salary": 10000, "hearing_rate": 10, "document_rate": 15, "source_rate": 20, "investigation_rate": 5, "quality_rate": 3}}, expected=(201,))
        assert commission["data"]["base_salary"] == 10000
        assert call("GET", f"/hr/{hr['id']}/subrecords")["total"] == 3
        call("DELETE", f"/hr/{hr['id']}/subrecords/{leave['id']}", expected=(204,))
        assert call("GET", f"/hr/{hr['id']}/subrecords?kind=leave")["total"] == 0
        hr_archive = multipart_upload("/attachments", {"record_id": hr["id"], "category": "员工档案", "remark": "人事档案验收"}, "employee-archive.txt", b"employee archive smoke")
        attachments.append(hr_archive["id"])
        assert any(item["id"] == hr_archive["id"] for item in call("GET", f"/attachments?record_id={hr['id']}")["items"])
        call("PATCH", f"/records/{hr['id']}", {"status": "在职"}, expected=(409,))
        call("POST", f"/records/{hr['id']}/transition", {"to_status": "在职", "comment": "绕过人事入口"}, expected=(409,))
        regularized = call("POST", f"/hr/{hr['id']}/transition", {"to_status": "在职", "effective_date": str(date.today()), "reason": "试用考核通过", "comment": "正式转正"})
        assert regularized["status"] == "在职" and regularized["data"]["regularized_at"] == str(date.today())
        call("POST", f"/hr/{hr['id']}/transition", {"to_status": "离职", "effective_date": str(date.today()), "reason": ""}, expected=(422,))
        offboarded = call("POST", f"/hr/{hr['id']}/transition", {"to_status": "离职", "effective_date": str(date.today()), "reason": "员工主动离职", "handover_to": "交接同事", "comment": "工作已交接"})
        assert offboarded["status"] == "离职" and offboarded["data"]["handover_to"] == "交接同事"
        warehouse = create_record("warehouse", "报废", "冒烟物品", {"category": "办公用品", "quantity": 1, "unit": "件", "location": "冒烟仓库"})
        assert warehouse["status"] == "在库" and warehouse["data"]["borrower"] == ""
        call("PATCH", f"/records/{warehouse['id']}", {"data": {**warehouse["data"], "borrower": "绕过借出"}}, expected=(409,))
        call("POST", f"/records/{warehouse['id']}/transition", {"to_status": "借出", "comment": "绕过仓库入口"}, expected=(409,))
        call("POST", f"/warehouse/{warehouse['id']}/borrow", {"borrower": "冒烟借用人", "due_date": str(date.today() - timedelta(days=1))}, expected=(422,))
        borrowed = call("POST", f"/warehouse/{warehouse['id']}/borrow", {"borrower": "冒烟借用人", "due_date": str(date.today() + timedelta(days=7)), "purpose": "接口验收", "comment": "借出"})
        assert borrowed["status"] == "借出" and borrowed["data"]["borrower"] == "冒烟借用人"
        call("POST", f"/warehouse/{warehouse['id']}/borrow", {"borrower": "重复借用", "due_date": str(date.today() + timedelta(days=7))}, expected=(409,))
        returning = call("POST", f"/warehouse/{warehouse['id']}/return", {"comment": "发起归还"})
        assert returning["status"] == "归还中"
        returned = call("POST", f"/warehouse/{warehouse['id']}/return-confirm", {"condition": "完好", "location": "冒烟仓库 A-01", "comment": "验收入库"})
        assert returned["status"] == "在库" and returned["data"]["borrower"] == "" and returned["data"]["last_borrower"] == "冒烟借用人"
        scrapped = call("POST", f"/warehouse/{warehouse['id']}/scrap", {"reason": "测试物品达到报废条件"})
        assert scrapped["status"] == "报废" and scrapped["data"]["scrap_reason"]
        passed("人事转正离职专用流程和仓库原子借还报废闭环")

        evidence_item = call("POST", "/warehouse/evidence", {
            "serial_no": serial("WH-EVIDENCE"),
            "warehouse": "上海一仓",
            "location": "A-01",
            "notary_no": serial("NOTARY"),
            "case_no": case["serial_no"],
            "shop_name": "冒烟证物店铺",
            "investigator": USERNAME,
            "notary_office": "冒烟公证处",
            "rights_holder": "冒烟权利人",
            "evidence_date": str(date.today()),
            "description": suffix,
        }, expected=(201,))
        records.append(evidence_item["id"])
        assert evidence_item["data"]["evidence_status"] == "未入库"
        call("POST", f"/warehouse/evidence/{evidence_item['id']}/check-out", {"recipient": "冒烟领取人", "purpose": "错误顺序"}, expected=(409,))
        evidence_item = call("POST", f"/warehouse/evidence/{evidence_item['id']}/check-in", {"warehouse": "上海一仓", "location": "A-01", "comment": "首次入库"})
        assert evidence_item["data"]["evidence_status"] == "已入库"
        call("POST", f"/warehouse/evidence/{evidence_item['id']}/check-in", {"warehouse": "上海一仓", "location": "A-01"}, expected=(409,))
        evidence_item = call("POST", f"/warehouse/evidence/{evidence_item['id']}/check-out", {"recipient": "冒烟领取人", "purpose": "庭审举证", "comment": "出库"})
        assert evidence_item["status"] == "借出" and evidence_item["data"]["evidence_status"] == "已出库"
        call("POST", f"/warehouse/evidence/{evidence_item['id']}/destroy", {"reason": "出库状态禁止销毁"}, expected=(409,))
        evidence_item = call("POST", f"/warehouse/evidence/{evidence_item['id']}/recheck-in", {"warehouse": "上海二仓", "location": "B-02", "condition": "完好", "comment": "验收入库"})
        assert evidence_item["status"] == "在库" and evidence_item["data"]["evidence_status"] == "已重新入库" and evidence_item["data"]["location"] == "B-02"
        evidence_item = call("POST", f"/warehouse/evidence/{evidence_item['id']}/destroy", {"reason": "证物保存期限届满，批准销毁"})
        assert evidence_item["status"] == "报废" and evidence_item["data"]["evidence_status"] == "已销毁"
        evidence_history = call("GET", f"/records/{evidence_item['id']}/history")["items"]
        assert {"证物登记", "证物入库", "证物出库", "证物重新入库", "证物销毁"}.issubset({event["action"] for event in evidence_history})
        passed("线索证物登记、入库、出库、重新入库、销毁及流程留痕")

        print(f"\nSMOKE_API_OK: {len(PASSED)} groups passed")
    finally:
        TOKEN = login(USERNAME, PASSWORD)["access_token"]
        if security_policy_original:
            try: call("PATCH", "/system/security-policy", {key: security_policy_original[key] for key in ["min_password_length", "max_failed_attempts", "lock_minutes", "token_minutes"]})
            except Exception: pass
        if system_menu_original:
            try:
                menu_item = next(item for item in call("GET", "/system/menus")["items"] if item["key"] == "task-reminders")
                call("PATCH", f"/system/menus/{menu_item['id']}", system_menu_original)
            except Exception: pass
        for key, value in system_configs_original.items():
            try: call("PATCH", f"/system/configs/{key}", {"value": value})
            except Exception: pass
        for item_id in reversed(system_parameters):
            try: call("DELETE", f"/system/parameters/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(system_menus):
            try: call("DELETE", f"/system/menus/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(agents):
            try: call("DELETE", f"/agent/documents/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(communications):
            try: call("DELETE", f"/communications/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(attachments):
            try: call("DELETE", f"/attachments/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(hearings):
            try: call("DELETE", f"/hearings/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(settlement_applications):
            try: call("DELETE", f"/finance/general-settlements/applications/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(incoming_payments):
            try: call("DELETE", f"/finance/incoming-payments/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(receivables):
            try: call("DELETE", f"/receivables/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(transactions):
            try: call("DELETE", f"/finance/transactions/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(reconciliations):
            try: call("DELETE", f"/finance/reconciliations/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(payment_packages):
            try: call("DELETE", f"/finance/payment-packages/{item_id}?reverse_paid=true", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(records):
            try:
                delete_status, _, _ = call("DELETE", f"/records/{item_id}", expected=(204, 404, 409), raw=True)
                if delete_status == 409:
                    call("DELETE", f"/testing/records/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(job_roles):
            try: call("DELETE", f"/hr/job-roles/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(departments):
            try: call("DELETE", f"/hr/departments/{item_id}", expected=(204, 404))
            except Exception: pass
        for item_id in reversed(templates):
            try: call("DELETE", f"/templates/{item_id}", expected=(204, 404, 409))
            except Exception: pass
        for item_id in reversed(users):
            try: call("DELETE", f"/system/users/{item_id}", expected=(204, 404))
            except Exception: pass

    record_remnants = []
    for module in ["customer", "contract", "case", "task", "finance", "finance_settlement", "document", "seal", "report", "hr", "warehouse", "investigation", "clue", "notary", "evidence"]:
        record_remnants.extend(call("GET", f"/records?module={module}&keyword=SMOKE&page_size=100")["items"])
    user_remnants = call("GET", "/system/users?keyword=smoke")["items"]
    template_remnants = [item for item in call("GET", "/templates")["items"] if item["name"].startswith("SMOKE-")]
    agent_remnants = [item for item in call("GET", "/agent/documents")["items"] if item["title"].startswith("冒烟")]
    attachment_remnants = [item for item in call("GET", "/attachments")["items"] if item["original_name"].startswith("smoke-")]
    notification_remnants = [item for item in call("GET", "/notifications")["items"] if "SMOKE" in (item.get("content") or "") or "冒烟" in (item.get("content") or "") or "SMOKE" in (item.get("title") or "") or "冒烟" in (item.get("title") or "")]
    escaped_suffix = suffix.replace("'", "''")
    test_notification_remnants = local_db_scalar(
        "SELECT count(*) FROM notifications "
        f"WHERE recipient LIKE '%{escaped_suffix}%' OR sender LIKE '%{escaped_suffix}%';",
        label="本轮测试账号通知残留",
    )
    orphan_task_notification_remnants = local_db_scalar(
        "SELECT count(*) FROM notifications n WHERE n.source_type='task' AND n.source_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.id=n.source_id AND b.module='task');",
        label="孤儿任务通知残留",
    )
    incoming_remnants = [item for item in call("GET", "/finance/incoming-payments")["items"] if item["receipt_no"].startswith("SMOKE-") or "冒烟" in item["payer_name"]]
    smoke_keyword = urllib.parse.quote("冒烟")
    department_remnants = [item for item in call("GET", f"/hr/departments?keyword={smoke_keyword}")["items"]]
    job_role_remnants = [item for item in call("GET", f"/hr/job-roles?keyword={smoke_keyword}")["items"]]
    if any([record_remnants, user_remnants, template_remnants, agent_remnants, attachment_remnants, notification_remnants, test_notification_remnants, orphan_task_notification_remnants, incoming_remnants, department_remnants, job_role_remnants]):
        raise AssertionError(
            "测试数据清理不完整："
            f"records={len(record_remnants)}, users={len(user_remnants)}, templates={len(template_remnants)}, "
            f"agents={len(agent_remnants)}, attachments={len(attachment_remnants)}, notifications={len(notification_remnants)}, "
            f"test_notifications={test_notification_remnants}, orphan_task_notifications={orphan_task_notification_remnants}, incoming={len(incoming_remnants)}, "
            f"departments={len(department_remnants)}, job_roles={len(job_role_remnants)}"
        )
    print("SMOKE_CLEANUP_OK: no test data remained")


if __name__ == "__main__":
    main()
