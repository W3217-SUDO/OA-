"""业务工具端到端（手动运行）：真实应用（隔离 SQLite）+ 登录 + 个人令牌 + /api/v1/mcp。用法：python tests/regression/agent_mcp_business_tools_e2e.py <apps/api-server 目录>"""
import asyncio, json, os, secrets, sys, uuid
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()  # apps/api-server
RUNTIME = ROOT / "tests" / ".runtime" / ("biz-" + uuid.uuid4().hex[:8])
RUNTIME.mkdir(parents=True)
PASSWORD = "Codex-Biz-" + secrets.token_hex(8)
os.environ.update(APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{RUNTIME}/oa_biz.db", UPLOAD_ROOT=str(RUNTIME / "uploads"),
                  INITIAL_ADMIN_PASSWORD=PASSWORD, REDIS_URL="redis://127.0.0.1:1/0", CACHE_REDIS_URL="")
sys.path.insert(0, str(ROOT))
import httpx  # noqa: E402
from tests.local_app import production_app as app  # noqa: E402

PREFIX = "CODEX-BIZ-" + uuid.uuid4().hex[:6]
results = []


def check(name, ok, info=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  " + str(info)[:1500]))


async def main():
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1", timeout=120) as http:
            r = await http.post("/api/v1/auth/login", data={"username": "admin", "password": PASSWORD})
            assert r.status_code == 200, r.text
            token = r.json()["access_token"]
            H = {"Authorization": "Bearer " + token}
            r = await http.patch("/api/v1/auth/me", json={"current_password": PASSWORD, "new_password": PASSWORD + "x"}, headers=H)
            assert r.status_code == 200, r.text
            r = await http.post("/api/v1/auth/login", data={"username": "admin", "password": PASSWORD + "x"})
            token = r.json()["access_token"]
            H = {"Authorization": "Bearer " + token}
            r = await http.post("/api/v1/agent-tools/access-tokens", json={"name": PREFIX, "days": 1}, headers=H)
            assert r.status_code in (200, 201), r.text
            pat = r.json()["token"]
            M = {"Authorization": "Bearer " + pat, "Accept": "application/json, text/event-stream", "Content-Type": "application/json",
                 "Origin": "http://127.0.0.1"}
            seq = iter(range(1, 10000))

            async def rpc(method, params=None, path="/api/v1/mcp"):
                r = await http.post(path, headers=M, json={"jsonrpc": "2.0", "id": next(seq), "method": method, "params": params or {}})
                text = r.text
                if text.startswith("event:") or "data:" in text[:20]:
                    text = next(line[5:].strip() for line in text.splitlines() if line.startswith("data:"))
                return r.status_code, json.loads(text) if text else None

            async def call(name, args, path="/api/v1/mcp"):
                status, body = await rpc("tools/call", {"name": name, "arguments": args}, path)
                res = (body or {}).get("result") or {}
                return res.get("structuredContent") or {}, bool(res.get("isError")), body

            status, init = await rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
            check("initialize", status == 200, init)
            status, listing = await rpc("tools/list")
            names = [tool["name"] for tool in listing["result"]["tools"]]
            biz = [n for n in names if n.startswith("biz_")]
            check("tools/list includes 31 business tools", len(biz) == 31, biz)

            # 1 新建客户：计划 → 执行
            cname = PREFIX + "客户有限公司"
            args = {"title": cname, "organization_type": "公司企业", "credit_code": "91310000" + uuid.uuid4().hex[:10].upper(),
                    "customer_managers": ["admin"], "invoice_title": cname, "taxpayer_id": "91310000TESTTAX",
                    "invoice_address": "上海测试路1号", "bank_name": "测试银行", "bank_account": "6222000000",
                    "contacts": [{"name": PREFIX + "联系人", "phone": "13800000000"}]}
            plan, err, raw = await call("biz_customer_create", args)
            check("customer_create plan has no writes", not err and plan.get("mode") == "计划" and all(s["status"] != "完成" for s in plan["steps"] if s["kind"] == "写"), raw)
            check("customer_create plan has no problems", not any(s.get("problem") for s in plan.get("steps", [])), plan.get("steps"))
            r = await http.get("/api/v1/customers", params={"customer_name": cname}, headers=H)
            check("plan did not create customer", not [x for x in r.json().get("items", []) if x.get("title") == cname], r.text[:300])
            done, err, raw = await call("biz_customer_create", {**args, "confirm": True})
            check("customer_create executed", not err and done.get("mode") == "执行" and all(s["status"] == "完成" for s in done["steps"]), raw)

            ov, err, raw = await call("biz_customer_overview", {"customer_name": cname})
            check("customer_overview finds customer and contact", not err and ov["customer"]["title"] == cname and len(ov["contacts"]) == 1, raw)

            mt, err, raw = await call("biz_customer_maintain", {"customer_name": cname, "profile": {"invoice_phone": "021-1234"},
                                                                 "note": {"content": PREFIX + "回访"}, "confirm": True})
            check("customer_maintain executed", not err and all(s["status"] == "完成" for s in mt["steps"]), raw)

            cc, err, raw = await call("biz_customer_conflict_check", {"name": cname})
            check("conflict_check", not err and cc.get("similar_customers"), raw)

            # 2 新建合同 + 提交审批
            import sqlite3
            conn = sqlite3.connect(RUNTIME / "oa_biz.db")
            conn.execute("INSERT INTO business_records(module,serial_no,title,customer,status,owner,department,description,data,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))",
                         ("hr", PREFIX + "-HR", "管理者", "", "在职", "admin", "上海分所", "", json.dumps({"username": "admin", "position": "律师"})))
            conn.execute("INSERT OR REPLACE INTO system_configs(key,label,\"group\",value,description,updated_by) VALUES(?,?,?,?,?,?)",
                         ("investigation_assignment", "调查任务分配", "investigation", json.dumps({"supervisor_username": "admin"}), "", "admin"))
            conn.commit(); conn.close()
            r = await http.put("/api/v1/contracts/approver-settings", json={"usernames": ["admin"]}, headers=H)
            check("(setup) contract approver list", r.status_code == 200, r.text[:300])
            r = await http.post("/api/v1/agent-tools/upload", files={"file": (PREFIX + "合同.pdf", b"%PDF-1.4\n%codex test\n%%EOF\n", "application/pdf")},
                                data={"category": "合同附件"}, headers=H)
            check("(setup) upload attachment", r.status_code in (200, 201), r.text[:300])
            attachment_id = r.json().get("id") or (r.json().get("attachment") or {}).get("id")
            ct = {"customer_name": cname, "title": PREFIX + "合同", "contract_type": "法律顾问合同", "fee_type": "固定收费",
                  "description": "测试", "amount": 1000, "signed_at": "2026-10-30", "external_contract_numbers": [PREFIX + "-EXT"], "attachment_ids": [attachment_id]}
            plan, err, raw = await call("biz_contract_create_and_submit", {**ct, "approvers": ["admin"]})
            check("contract plan ok", not err and not any(s.get("problem") for s in plan["steps"]), raw)
            done, err, raw = await call("biz_contract_create_and_submit", {**ct, "approvers": ["admin"], "confirm": True})
            check("contract created and submitted", not err and all(s["status"] == "完成" for s in done["steps"]), raw)
            contract_no = (done.get("contract") or {}).get("serial_no")
            ov, err, raw = await call("biz_contract_overview", {"contract_no": contract_no})
            check("contract_overview", not err and ov["contract"]["serial_no"] == contract_no, raw)

            contract_id = ov["contract"]["id"] if not err else None
            r = await http.post(f"/api/v1/contracts/{contract_id}/approve", json={"approved": True, "comment": "测试审批"}, headers=H)
            pass

            ch, err, raw = await call("biz_contract_change", {"contract_no": contract_no, "change_type": "期限变更", "reason": "续期",
                                                              "end_date": "2027-12-31", "approvers": ["admin"]})
            check("contract_change plan", not err and ch["mode"] == "计划", raw)

            cs = {"contract_no": contract_no, "title": PREFIX + "案件", "case_type": "民事案件", "client_position": "原告/申请人",
                  "handling_lawyers": ["admin"], "cause_or_charge": "侵害商标权纠纷", "defendants": [{"name": PREFIX + "被告公司", "organization_type": "公司企业", "identity_no": "91310000MA1TEST01X"}]}
            plan, err, raw = await call("biz_case_create_from_contract", cs)
            check("case_create plan", not err and not any(x.get("problem") for x in plan["steps"]), raw)
            done, err, raw = await call("biz_case_create_from_contract", {**cs, "confirm": True})
            check("case created with litigants", not err and all(x["status"] == "完成" for x in done["steps"]), raw)
            case_no = (done.get("case") or {}).get("serial_no")

            case_id = (done.get("case") or {}).get("id")
            r = await http.post(f"/api/v1/cases/{case_id}/creation/review", json={"approved": True, "comment": "测试通过"}, headers=H)
            check("(setup) case creation approved via web API", r.status_code in (200, 201) and '"IsSuccess":false' not in r.text, r.text[:300])
            ov, err, raw = await call("biz_case_overview", {"case_no": case_no})
            check("case_overview", not err and ov["case"]["serial_no"] == case_no, raw)

            el, err, raw = await call("biz_case_fill_payment_elements", {"case_no": case_no, "court": {"court": "上海知识产权法院", "court_case_no": "(2026)沪73民初1号", "hearing_date": "2026-12-01"},
                                                                         "people": {"hearing_lawyer": "admin"}, "confirm": True})
            check("fill payment elements", not err and all(x["status"] == "完成" for x in el["steps"]), raw)

            fee = {"case_no": case_no, "expense_scope": "律所", "fee_type": "官费", "expense_subtype": "诉讼费", "title": "一审诉讼费",
                   "amount": 200, "handler": "admin", "court": "上海知识产权法院"}
            plan, err, raw = await call("biz_case_fee_create_and_request_payment", fee)
            check("fee plan", not err and not any(x.get("problem") for x in plan["steps"]), raw)
            done, err, raw = await call("biz_case_fee_create_and_request_payment", {**fee, "confirm": True})
            check("fee created", not err and all(x["status"] == "完成" for x in done["steps"]), raw)
            fee_id = (done.get("fee") or {}).get("id")
            ref, err, raw = await call("biz_case_court_refund", {"case_no": case_no, "fee_id": fee_id, "amount": 50})
            check("court_refund plan", not err and ref["mode"] == "计划", raw)
            ref, err, raw = await call("biz_case_court_refund", {"case_no": case_no, "fee_id": fee_id, "amount": 50, "confirm": True})
            print("INFO court_refund execute:", "ERR" if err else "ok", json.dumps(ref, ensure_ascii=False)[:400])
            inv, err, raw = await call("biz_case_invoice_request", {"case_no": case_no})
            print("INFO case_invoice plan:", "ERR" if err else "ok", json.dumps(ref if not err else (raw.get("result") or {}).get("structuredContent"), ensure_ascii=False)[:300])
            check("case_invoice plan gives clear answer", (not err) or "开票" in json.dumps(raw, ensure_ascii=False), raw)
            pay, err, raw = await call("biz_contract_payment_request", {"contract_no": contract_no, "application_date": "2026-10-30"})
            check("contract_payment plan gives clear answer", (not err) or "付款" in json.dumps(raw, ensure_ascii=False), raw)
            print("INFO contract_payment plan:", "ERR" if err else "ok", json.dumps((raw.get("result") or {}).get("structuredContent"), ensure_ascii=False)[:300])
            ar, err, raw = await call("biz_case_archive_apply", {"case_no": case_no, "archive_type": "正常归档"})
            check("archive plan", not err and ar["mode"] == "计划" and ar.get("readiness") is not None, raw)

            ip, err, raw = await call("biz_investigation_task_publish", {"contract_no": contract_no, "right_type": "商标", "customer_review": False,
                                                                         "authorized_from": "2026-10-01", "authorized_to": "2027-09-30",
                                                                         "investigation_region": "全国", "authorization_scope": "全国", "owner": "admin", "confirm": True})
            check("investigation published", not err and all(x["status"] == "完成" for x in ip["steps"]), raw)
            inv_no = (ip.get("investigation") or {}).get("serial_no")
            st, err, raw = await call("biz_investigation_subtask_assign", {"investigation_no": inv_no, "title": PREFIX + "子任务", "investigator": "admin",
                                                                            "deadline": "2026-11-30", "investigation_regions": [["上海市"]], "confirm": True})
            check("subtask assigned", not err and all(x["status"] == "完成" for x in st["steps"]), raw)
            cl, err, raw = await call("biz_clue_create", {"task_no": inv_no, "sales_channel": "电商平台", "product": PREFIX + "产品", "shop_name": PREFIX + "店",
                                                          "investigated_at": "2026-10-30", "submit": True, "confirm": True})
            check("clue created and submitted", not err and all(x["status"] == "完成" for x in cl["steps"]), raw)
            clue_no = (cl.get("clue") or {}).get("serial_no")
            mc, err, raw = await call("biz_my_clues", {"status_group": "待审核"})
            check("my_clues lists submitted clue", not err and any(c.get("serial_no") == clue_no for c in mc["clues"]), raw)
            rv, err, raw = await call("biz_clue_review", {"clue_no": clue_no, "approved": True, "comment": "可以", "confirm": True})
            check("clue_review becomes pending web confirmation", not err and any(x["status"] == "待网页确认" for x in rv["steps"]), raw)
            clue_id = (cl.get("clue") or {}).get("id")
            r = await http.post(f"/api/v1/investigations/clues/{clue_id}/review", json={"approved": True, "comment": "测试通过"}, headers=H)
            check("(setup) clue approved via web API", r.status_code in (200, 201) and '"IsSuccess":false' not in r.text, r.text[:300])
            co, err, raw = await call("biz_clue_register_collection", {"clue_nos": [clue_no], "collected_at": "2026-10-30", "notary_institution": "上海市东方公证处", "confirm": True})
            check("clue collection registered", not err and all(x["status"] == "完成" for x in co["steps"]), raw)
            tc, err, raw = await call("biz_clues_to_cases", {"clue_nos": [clue_no], "client_position": "原告/申请人", "case_phase": "新案待分配", "handling_lawyer": "admin"})
            check("clues_to_cases plan", not err and tc["mode"] == "计划", raw)
            tasks = await http.get("/api/v1/tasks", params={"page_size": 5}, headers=H)
            task_rows = tasks.json().get("items", []) if tasks.status_code == 200 else []
            mine = [t for t in task_rows if PREFIX in str(t.get("title"))]
            if mine:
                ta, err, raw = await call("biz_task_act", {"task_id": mine[0]["id"], "action": "reject"})
                check("task_act reject without reason refused", err, raw)
                ta, err, raw = await call("biz_task_act", {"task_id": mine[0]["id"], "action": "feedback", "comment": "进展如何", "confirm": True})
                check("task_act feedback", not err, raw)

            ir, err, raw = await call("biz_incoming_payment_register", {"received_date": "2026-10-30", "amount": 300, "payer_name": cname,
                                                                        "bank_reference": PREFIX + "-BANK", "customer": cname, "confirm": True})
            check("incoming payment registered", not err and all(x["status"] == "完成" for x in ir["steps"]), raw)

            # 3 读工具
            for name, a in [("biz_dashboard_todo", {}), ("biz_my_clues", {"status_group": "待提交"}), ("biz_my_payment_requests", {}),
                            ("biz_incoming_payment_find", {}), ("biz_settlement_apply", {})]:
                res, err, raw = await call(name, a)
                check(f"{name} runs", not err, raw)

            # 4 任务
            t, err, raw = await call("biz_task_create", {"title": PREFIX + "任务", "owner": "admin", "deadline": "2026-11-20", "confirm": True})
            check("task_create", not err and all(s["status"] == "完成" for s in t["steps"]), raw)

            # 5 输入校验与未知工具
            res, err, raw = await call("biz_customer_create", {"title": "x"})
            check("schema validation rejects missing required", err, raw)
            res, err, raw = await call("biz_case_overview", {"case_no": PREFIX + "-NOPE"})
            check("case_overview not found is error", err, raw)

            # 6 业务范围：只选 case 业务时看不到客户写工具
            status, listing = await rpc("tools/list", path="/api/v1/mcp?biz=case,workbench")
            scoped = [tool["name"] for tool in (listing or {}).get("result", {}).get("tools", []) if tool["name"].startswith("biz_")]
            check("biz=case,workbench shows case tools and hides customer tools", "biz_customer_create" not in scoped and "biz_case_fill_payment_elements" in scoped, scoped)
            res, err, raw = await call("biz_customer_create", {**args, "title": cname + "2"}, path="/api/v1/mcp?biz=case")
            check("out-of-scope business tool refused", err, raw)

            # 7 普通账号、只读令牌：看不到业务写工具，调用写工具被拒
            uname = "codex-biz-" + uuid.uuid4().hex[:6]
            r = await http.post("/api/v1/system/users", json={"username": uname, "display_name": "测试律师", "department": "上海分所",
                                                             "password": "Codex-Biz-User-123!", "role": "user", "profile": {"position": "律师"}}, headers=H)
            check("(setup) normal user", r.status_code in (200, 201), r.text[:300])
            uid = r.json().get("id")
            r = await http.patch(f"/api/v1/system/users/{uid}/permissions", json={"action_keys": ["agent.mcp.personal_token"]}, headers=H)
            check("(setup) grant read-only MCP token", r.status_code == 200, r.text[:300])
            r = await http.post("/api/v1/auth/login", data={"username": uname, "password": "Codex-Biz-User-123!"})
            utok = r.json().get("access_token")
            if True:
                await http.patch("/api/v1/auth/me", json={"current_password": "Codex-Biz-User-123!", "new_password": "Codex-Biz-User-456!"},
                                 headers={"Authorization": "Bearer " + (utok or "")})
                r = await http.post("/api/v1/auth/login", data={"username": uname, "password": "Codex-Biz-User-456!"})
                utok = r.json().get("access_token")
            r = await http.post("/api/v1/agent-tools/access-tokens", json={"name": PREFIX + "u", "days": 1}, headers={"Authorization": "Bearer " + str(utok)})
            print("INFO user token:", r.status_code, r.text[:200] if r.status_code >= 300 else "")
            if r.status_code in (200, 201):
                M["Authorization"] = "Bearer " + r.json()["token"]
                status, listing = await rpc("tools/list")
                names = [t["name"] for t in listing["result"]["tools"] if t["name"].startswith("biz_")]
                writes = [n for n in names if n in ("biz_customer_create", "biz_case_fee_create_and_request_payment")]
                check("read-only user token hides business write tools", names and not writes, names)
                res, err, raw = await call("biz_customer_create", {**args, "title": cname + "3"})
                check("read-only user token refused write tool", err, raw)
                res, err, raw = await call("biz_customer_overview", {"customer_name": cname})
                check("normal user cannot see admin's customer (data scope kept)", err, raw)

    print(f"\n{sum(ok for _, ok in results)}/{len(results)} passed; runtime dir {RUNTIME}")


asyncio.run(main())
