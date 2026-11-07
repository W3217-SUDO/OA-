"""沪知旧系统 → 新 OA 定时同步（在新生产上跑，每 15 分钟）。

对旧系统只读：经 SSH 隧道连 47 的 SQL Server，只发 SELECT（NOLOCK、MAXDOP 1、逐表顺序），
每张表前看一次 47 的负载，忙就等；连续忙就本轮放弃，下一轮再来。
拉取水位线之后的变化，对照生产镜像表分成 新增 / 改动 / 主键被新系统占用，写报告。
--write 时再按表增量写入生产（lib/hz_live_write.py，一轮一个事务，改前原值写进 backups/，可回滚）；
不带 --commit 只演算后回滚。--nightly 另对一遍旧系统每天自动重算的案件期限。陶威 10-31 21:50 回“开”后启用写入。

用法：hz_live_sync.py --state <状态.json> --report-dir <目录> [--write [--commit]] [--nightly]
"""
import argparse, json, os, signal, subprocess, sys, time
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pymssql

PRIVATE = Path("/opt/sunhold-oa/private/hz-sync")
TUNNEL_PORT = 14330
SKIP = {"SYS_Log", "Legal_Case_Task_Message"}  # 日志/大消息表不同步
FULL = {"CRM_Customer_Coordinator", "Legal_Case_Participant", "Legal_Case_Event", "HR_Staff", "HR_Staff_File",
        "HR_Staff_OffWorkDay", "HR_Role_Permissions", "FAM_AR_CaseFee"}  # 旧系统会物理删 / ChangeTime 不可靠
OVERLAP = timedelta(minutes=10)
LIB = "/opt/sunhold-oa/hz-sync/lib"
BACKUP_DIR = Path("/opt/sunhold-oa/hz-sync/backups")
NATIVE_FILE = Path("/opt/sunhold-oa/hz-sync/native.json")
MODE = "dry-run"
FAILED_DETAIL = None
LOAD_LIMITS = {"sql_cpu": 50, "total_cpu": 80, "free_mb": 600, "active_requests": 8}


def env():
    return dict(l.strip().split("=", 1) for l in open(PRIVATE / "hz_sa.env") if "=" in l)


def ssh(host_key, host, *args, forward=None):
    cmd = ["ssh", "-i", str(PRIVATE / host_key), "-o", "IdentitiesOnly=yes", "-o", f"UserKnownHostsFile={PRIVATE / 'known_hosts'}",
           "-o", "StrictHostKeyChecking=yes", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=30"]
    if forward:
        cmd += ["-o", "ExitOnForwardFailure=yes", "-N", "-L", forward]
    return cmd + [f"Administrator@{host}", *args]


class Tunnel:
    def __enter__(self):
        self.proc = subprocess.Popen(ssh("legacy47_ed25519", "47.101.188.36", forward=f"{TUNNEL_PORT}:127.0.0.1:1433"),
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(30):
            if self.proc.poll() is not None:
                raise SystemExit("隧道没起来：" + self.proc.stderr.read().decode(errors="replace")[-300:])
            try:
                import socket
                socket.create_connection(("127.0.0.1", TUNNEL_PORT), timeout=1).close()
                return self
            except OSError:
                time.sleep(1)
        raise SystemExit("隧道超时")

    def __exit__(self, *exc):
        self.proc.send_signal(signal.SIGTERM)
        self.proc.wait(timeout=10)


def connect_legacy():
    e = env()
    # 旧库 SQL Server 2012 只接受 TDS 7.0（实测更高版本握手失败）；已核对取回的值与本机副本逐字段一致。
    return pymssql.connect(server="127.0.0.1", port=TUNNEL_PORT, user=e["HZ_USER"], password=e["HZ_SA_PASSWORD"],
                           database=e["HZ_DB"], login_timeout=15, timeout=120, appname="oa-hz-sync-readonly", tds_version="7.0")


def load_47(cur):
    cur.execute("""SELECT TOP 1 r.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]','int'),
        r.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]','int')
        FROM (SELECT CONVERT(xml, record) r, timestamp FROM sys.dm_os_ring_buffers WHERE ring_buffer_type=N'RING_BUFFER_SCHEDULER_MONITOR' AND record LIKE '%<SystemHealth>%') x ORDER BY timestamp DESC""")
    sql_cpu, idle = cur.fetchone()
    cur.execute("SELECT available_physical_memory_kb/1024 FROM sys.dm_os_sys_memory"); free_mb = int(cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE is_user_process=1"); sessions = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sys.dm_exec_requests WHERE session_id<>@@SPID AND session_id>50"); active = cur.fetchone()[0]
    return {"sql_cpu": sql_cpu, "total_cpu": 100 - idle, "free_mb": free_mb, "sessions": sessions, "active_requests": active}


def busy(r):
    return (r["sql_cpu"] > LOAD_LIMITS["sql_cpu"] or r["total_cpu"] > LOAD_LIMITS["total_cpu"]
            or r["free_mb"] < LOAD_LIMITS["free_mb"] or r["active_requests"] > LOAD_LIMITS["active_requests"])


def q(name):
    return "[" + name.replace("]", "]]") + "]"


def pg_dsn():
    for line in open("/opt/sunhold-oa/private/production-native.env"):
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"')
            return url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")
    raise SystemExit("找不到 DATABASE_URL")


def norm(v):
    """两边取值换成同一写法再比：日期去时区、补齐毫秒；数字去多余的 0；GUID 大写。"""
    from decimal import Decimal, InvalidOperation
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.replace(tzinfo=None).isoformat(timespec="milliseconds")
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float, Decimal)):
        return format(Decimal(str(v)).normalize(), "f")
    if hasattr(v, "hex") and not isinstance(v, str):
        return str(v).upper()
    text = str(v).strip()
    if len(text) >= 19 and text[4] == "-" and text[10] in "T ":
        try:
            return datetime.fromisoformat(text.replace(" ", "T")).replace(tzinfo=None).isoformat(timespec="milliseconds")
        except ValueError:
            pass
    try:
        if text and text.lstrip("-").replace(".", "", 1).isdigit():
            return format(Decimal(text).normalize(), "f")
    except InvalidOperation:
        pass
    if len(text) == 36 and text.count("-") == 4:
        return text.upper()
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--report-dir", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--nightly", action="store_true")
    args = ap.parse_args()
    global MODE
    MODE = "live" if args.write and args.commit else "write-rehearsal" if args.write else "dry-run"
    delta, pks = {}, {}
    native = {t: set(v) for t, v in json.load(open(NATIVE_FILE)).items()} if NATIVE_FILE.exists() else None
    state = json.load(open(args.state)) if os.path.exists(args.state) else {"watermark": "2026-10-30 20:50:00"}
    started = datetime.now()
    wm = state["watermark"]
    report = {"started": started.isoformat(timespec="seconds"), "watermark": wm, "load_47": [], "load_139": None, "tables": {}, "paused": 0}
    pg = psycopg.connect(pg_dsn(), autocommit=True)
    pg.execute("SET default_transaction_read_only = on")
    with Tunnel():
        legacy = connect_legacy(); cur = legacy.cursor()
        cur.execute("SELECT t.name FROM sys.tables t ORDER BY t.name"); tables = [r[0] for r in cur.fetchall() if r[0] not in SKIP]
        for t in tables:
            for attempt in range(10):
                r = load_47(cur); r["before"] = t; report["load_47"].append(r)
                if not busy(r):
                    break
                report["paused"] += 1; time.sleep(60)
            else:
                report["aborted"] = f"47 持续繁忙，停在 {t}"; break
            cur.execute("""SELECT k.name FROM sys.indexes i JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
                JOIN sys.columns k ON k.object_id=ic.object_id AND k.column_id=ic.column_id WHERE i.object_id=OBJECT_ID(%s) AND i.is_primary_key=1 ORDER BY ic.key_ordinal""", (t,))
            pk = [x[0] for x in cur.fetchall()]
            pks[t] = pk
            cur.execute("SELECT name, system_type_id, max_length FROM sys.columns WHERE object_id=OBJECT_ID(%s) AND is_computed=0 AND system_type_id<>189 ORDER BY column_id", (t,))
            meta = cur.fetchall()
            names = [x[0] for x in meta]
            # varchar/char/text 在 TDS 7.0 下按服务器 GBK 字节传回、这里的 FreeTDS 会当 Latin-1 解码成乱码；
            # 在库里先转成 nvarchar，由 SQL Server 自己转成 Unicode 再传。
            exprs = [f"CAST({q(n)} AS NVARCHAR({min(m, 4000)})) AS {q(n)}" if st in (167, 175) and 0 < m <= 8000
                     else f"CAST({q(n)} AS NTEXT) AS {q(n)}" if st == 35 or (st == 167 and m == -1)
                     else q(n) for n, st, m in meta]
            has_time = [c for c in ("ChangeTime", "CreateTime") if c in names]
            if not pk:
                continue
            if t in FULL and args.nightly:
                # 会物理删除 / 修改时间不可靠的表：夜间整表拉一遍，和镜像对不上的行照常写（相同的写入时会跳过）
                cur.execute(f"SELECT {','.join(exprs)} FROM {q(t)} WITH (NOLOCK) OPTION (MAXDOP 1)")
            elif not has_time:
                continue
            else:
                # 15 分钟一轮按时间取增量（这几张表的新建行时间可靠，改动由夜间整表补）
                cond = " OR ".join(f"{q(c)} >= %s" for c in has_time)
                cur.execute(f"SELECT {','.join(exprs)} FROM {q(t)} WITH (NOLOCK) WHERE {cond} OPTION (MAXDOP 1)", tuple(wm for _ in has_time))
            rows = cur.fetchall()
            exists = pg.execute("SELECT to_regclass(%s)", (f'public."{t}"',)).fetchone()[0]
            if t == "Legal_Case" and args.nightly and exists:
                # 旧系统作业改阶段不改 ChangeTime：夜间按阶段整表对一遍，只取变了的行。
                # 期限 1.2.155 起新系统按任务实时算，不再对（陶威 11-02 “期限同意”）
                have = {str(r[names.index("CaseId")]) for r in rows}
                mirror_dl = {str(a): norm(c) for a, c in pg.execute('SELECT "CaseId", "CasePhaseId" FROM "Legal_Case"')}
                cur.execute("SELECT CaseId, CasePhaseId FROM Legal_Case WITH (NOLOCK) OPTION (MAXDOP 1)")
                extra = [str(a) for a, c in cur.fetchall() if str(a) in mirror_dl and str(a) not in have and mirror_dl[str(a)] != norm(c)]
                for i in range(0, len(extra), 500):
                    cur.execute(f"SELECT {','.join(exprs)} FROM Legal_Case WITH (NOLOCK) WHERE CaseId IN ({','.join(extra[i:i + 500])}) OPTION (MAXDOP 1)")
                    rows += cur.fetchall()
                report["nightly_deadline_rows"] = len(extra)
            if not rows:
                continue
            if exists and len(pk) == 1:
                delta[t] = {"pk": pk[0], "rows": [dict(zip(names, r)) for r in rows]}
            entry = {"rows": len(rows), "new": 0, "changed": 0, "same": 0, "no_mirror_table": not exists}
            if exists and len(pk) == 1:
                k = names.index(pk[0])
                mirror = {norm(m[0]): m for m in pg.execute(
                    f'SELECT "{pk[0]}"::text, row_to_json(x)::text FROM "{t}" x WHERE "{pk[0]}"::text = ANY(%s)', ([str(r[k]) for r in rows],))}
                for r in rows:
                    m = mirror.get(norm(r[k]))
                    if not m:
                        entry["new"] += 1; continue
                    old = json.loads(m[1])
                    diff = [n for i, n in enumerate(names) if n in old and norm(old[n]) != norm(r[i]) and n not in ("ChangeTime",)]
                    if any(n.endswith("Guid") for n in diff):
                        # 主键相同但 GUID 不同：这个主键被新系统自己写的镜像行占了，写入时新系统那行要换号
                        entry["id_taken_by_new_system"] = entry.get("id_taken_by_new_system", 0) + 1; continue
                    entry["changed" if diff else "same"] += 1
                    if diff:
                        entry.setdefault("changed_columns", {})
                        for n in diff:
                            entry["changed_columns"][n] = entry["changed_columns"].get(n, 0) + 1
            report["tables"][t] = entry
        if args.write and native is None and not report.get("aborted"):
            native = build_native(cur, pg, pks)
            report["native_start_list"] = {t: len(v) for t, v in native.items()}
        report["load_47"].append({**load_47(cur), "before": "end"})
        legacy.close()
    # 139 负载（只读 wmic），附件上传前要看
    out = subprocess.run(ssh("legacy139_ed25519", "139.224.35.141", "wmic cpu get loadpercentage /value & wmic os get FreePhysicalMemory /value"),
                         capture_output=True, text=True, timeout=60).stdout
    vals = dict(l.strip().split("=", 1) for l in out.splitlines() if "=" in l)
    report["load_139"] = {"cpu": int(vals.get("LoadPercentage", -1)), "free_mb": int(vals.get("FreePhysicalMemory", 0)) // 1024}
    if args.write and not report.get("aborted"):
        report["oss_index"] = refresh_oss_index(report["load_139"])
        report["case_files_upload"] = upload_case_dirs(report["load_139"], delta)
        report["other_files_upload"] = upload_other_dirs(report["load_139"], delta, pg)
        report["write"] = write_round(args, delta, native, pks, started, state)
    report["finished"] = datetime.now().isoformat(timespec="seconds")
    report["mode"] = MODE
    Path(args.report_dir).mkdir(parents=True, exist_ok=True)
    out_file = Path(args.report_dir) / f"hz-sync-{started:%Y%m%d-%H%M}.json"
    json.dump(report, open(out_file, "w"), ensure_ascii=False, indent=1, default=str)
    # 试跑：水位线不前移，每轮都从同一点看全部变化；正式写入时才前移到本轮开始时间减重叠
    if args.write and args.commit and not report.get("aborted"):
        report["alignment"] = alignment_check(state, args.state)
    failed = dict((report.get("write") or {}).get("report", {}).get("step_failed") or {})
    if (report.get("alignment") or {}).get("worse"):
        failed["alignment"] = "新旧条数对不上（比基线多缺）：" + json.dumps(report["alignment"]["worse"], ensure_ascii=False)
    promo = (report.get("write") or {}).get("ap_promotion") or {}
    if promo.get("exit") not in (None, 0):
        failed["ap_promotion"] = promo.get("output", "")[-300:]
    status = "aborted" if report.get("aborted") else "partial" if failed else "ok"
    if failed:
        report["step_failed"] = failed
        global FAILED_DETAIL
        FAILED_DETAIL = "已写入，但这几步没做成：" + json.dumps(failed, ensure_ascii=False)[:400]
    if report.get("alignment") or failed:
        json.dump(report, open(out_file, "w"), ensure_ascii=False, indent=1, default=str)  # 带上核对结果再存一遍
    print(json.dumps({"status": status, "report": str(out_file), "tables": len(report["tables"]), "paused": report["paused"],
                      "max_sql_cpu": max(x["sql_cpu"] for x in report["load_47"]), "load_139": report["load_139"]}, ensure_ascii=False))
    return status


NATIVE_TABLES = ("CRM_Customer", "CRM_Customer_Contacts", "FCM_Contract", "Legal_Case", "Legal_Investigation", "Legal_Investigation_Task",
                 "Legal_Investigation_Clue", "Legal_Investigation_Clue_Evidence", "IPR_Case", "IPR_CaseType", "Legal_Investigation_Clue_File",
                 "Legal_Investigation_Clue_Producer", "Legal_Investigation_Clue_Product", "Legal_Investigation_Clue_Indictee", "AWS_OfficialDocument",
                 "CRM_Customer_Coordinator", "BAS_Warehouse", "BAS_Warehouse_StorageLocation", "HR_Department", "BAS_Case_Phase", "IPR_CasePhase", "IPR_User")


OSS_INDEX = Path("/opt/sunhold-oa/hz-sync/oss_index")
OSSUTIL = r"F:\OSS-Transfer-Tools\ossutil-2.4.0-windows-amd64-go1.20\ossutil.exe"
OSS_ARGS = "--mode EcsRamRole --endpoint oss-cn-shanghai-internal.aliyuncs.com --region cn-shanghai"
OSS_DIRS = {"OfficialMetaFiles": ("D:/HZ.CRM/HZ.CRM.WEB/CaseFiles/OfficialMetaFiles/", "oss://oabeifen3217/HZ.CRM/HZ.CRM.WEB/CaseFiles/OfficialMetaFiles/")}


def refresh_oss_index(load_139):
    """139 上旧系统的原文件：近两天新增/改过的先用 139 自带的 ossutil 低优先级直传 OSS（单个、不落临时文件），
    再列出 OSS 上的文件做索引，写入程序按索引只给 OSS 上真有文件的记录建附件。139 忙（CPU>50%）就只列不传。"""
    import re as _re
    OSS_INDEX.mkdir(mode=0o700, exist_ok=True)
    out = {}
    for name, (src, dst) in OSS_DIRS.items():
        entry = {}
        if load_139 and 0 <= load_139.get("cpu", 100) <= 50:
            up = subprocess.run(ssh("legacy139_ed25519", "139.224.35.141",
                                    f'start "" /low /b /wait {OSSUTIL} cp -r -u {src} {dst} --max-age 2d --job 1 --parallel 1 --checkers 1 --no-progress {OSS_ARGS}'),
                                capture_output=True, text=True, timeout=600)
            entry["upload"] = (up.stdout or up.stderr).strip().splitlines()[-2:] if (up.stdout or up.stderr) else []
        else:
            entry["upload"] = "skipped: 139 busy"
        ls = subprocess.run(ssh("legacy139_ed25519", "139.224.35.141", f"{OSSUTIL} ls {dst} {OSS_ARGS}"), capture_output=True, text=True, timeout=600)
        files = {}
        for line in ls.stdout.splitlines():
            m = _re.search(r"\s(\d+)\s+Standard\s+(\w+)\s+(oss://\S+/" + name + r"/([0-9a-fA-F-]{36})/(.+))$", line.strip())
            if m and m.group(5):
                files.setdefault(m.group(4).upper(), []).append({"size": int(m.group(1)), "etag": m.group(2), "path": m.group(3), "name": m.group(5)})
        if ls.returncode == 0 and files:
            tmp = OSS_INDEX / (name + ".json.tmp"); json.dump(files, open(tmp, "w"), ensure_ascii=False); tmp.replace(OSS_INDEX / (name + ".json"))
        entry["files"] = len(files); entry["ls_ok"] = ls.returncode == 0
        out[name] = entry
    return out


def upload_case_dirs(load_139, delta):
    """501385：本轮新增/改动的旧案件附件所在目录，139 不忙时低优先级直传 OSS（-u 只传新的；每轮最多 40 个目录）。"""
    from case_files_sync import case_dirs_for_upload
    dirs = case_dirs_for_upload(delta)[:40]
    if not dirs:
        return {"dirs": 0}
    if not (load_139 and 0 <= load_139.get("cpu", 100) <= 50):
        return {"dirs": len(dirs), "upload": "skipped: 139 busy"}
    done, failed = 0, []
    for case in dirs:
        src = f"D:/HZ.CRM/HZ.CRM.WEB/CaseFiles/CaseFiles/{case}/"
        dst = f"oss://oabeifen3217/HZ.CRM/HZ.CRM.WEB/CaseFiles/CaseFiles/{case}/"
        up = subprocess.run(ssh("legacy139_ed25519", "139.224.35.141",
                                f'start "" /low /b /wait {OSSUTIL} cp -r -u {src} {dst} --max-age 2d --job 1 --parallel 1 --checkers 1 --no-progress {OSS_ARGS}'),
                            capture_output=True, text=True, timeout=300)
        if up.returncode == 0:
            done += 1
        else:
            failed.append(case)
    return {"dirs": len(dirs), "uploaded": done, "failed": failed[:10]}


def upload_other_dirs(load_139, delta, pg):
    """陶威 11-05“A”：本轮新增/改动的线索、取证、发票、用印、合同附件所在目录，139 不忙时低优先级直传 OSS（-u 只传新的；每轮最多 40 个目录）。"""
    from other_files_sync import dirs_for_upload
    dirs = dirs_for_upload(pg, delta)[:40]
    if not dirs:
        return {"dirs": 0}
    if not (load_139 and 0 <= load_139.get("cpu", 100) <= 50):
        return {"dirs": len(dirs), "upload": "skipped: 139 busy"}
    done, failed = 0, []
    for d in dirs:
        up = subprocess.run(ssh("legacy139_ed25519", "139.224.35.141",
                                f'start "" /low /b /wait {OSSUTIL} cp -r -u D:/{d}/ oss://oabeifen3217/{d}/ --max-age 2d --job 1 --parallel 1 --checkers 1 --no-progress {OSS_ARGS}'),
                            capture_output=True, text=True, timeout=300)
        if up.returncode == 0:
            done += 1
        else:
            failed.append(d.rsplit("/", 1)[-1])
    return {"dirs": len(dirs), "uploaded": done, "failed": failed[:10]}


ALIGN_CHECKS = {
    # 名称：旧系统有、新系统没有对应记录的条数（只数旧系统行：主键 < 1000 万、编号不带 -R）
    # 陶威 11-03 12:10：旧没有的、只在新系统的、任一边已删的都不算没对齐——只数旧系统有效的行；新系统已删的仍算“有对应”
    "客户": """SELECT count(*) FROM "CRM_Customer" s WHERE upper(coalesce(s."IsActived",'T'))='T' AND "CustomerId" < 10000000 AND "CustomerNo" NOT LIKE '%-R' AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='customer' AND b.serial_no=trim(s."CustomerNo"))""",
    "合同": """SELECT count(*) FROM "FCM_Contract" s WHERE upper(coalesce(s."IsActived",'T'))='T' AND "ContractId" < 10000000 AND "ContractNo" NOT LIKE '%-R' AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='contract' AND b.serial_no=trim(s."ContractNo"))""",
    "案件": """SELECT count(*) FROM "Legal_Case" s WHERE upper(coalesce(s."IsActived",'T'))='T' AND "CaseId" < 10000000 AND "CaseNo" NOT LIKE '%-R' AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='case' AND b.serial_no=trim(s."CaseNo"))""",
    "线索": """SELECT count(*) FROM "Legal_Investigation_Clue" s WHERE upper(coalesce(s."IsActived",'T'))='T' AND "ClueId" < 10000000 AND "ClueNo" NOT LIKE '%-R' AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='clue' AND b.serial_no=trim(s."ClueNo"))""",
    "用印申请": """SELECT count(*) FROM "AWS_OfficialDocument" s WHERE upper(coalesce(s."IsActived",'T'))='T' AND "OfficialDocumentId" < 10000000 AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='official_outgoing' AND b.serial_no=trim(s."OfficialDocumentNo"))""",
    "案件费用": """SELECT count(*) FROM "FAM_AR_CaseFee" s WHERE upper(coalesce(s."IsActived",'T'))='T' AND "CaseFeeId" < 10000000 AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='finance' AND b.serial_no='HZ-FEE-'||s."CaseFeeId")""",
    "请款单": """SELECT count(*) FROM legacy_finance_records l WHERE l.source_table='FAM_AP_Payment' AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='contract_payment' AND b.data->>'legacy_finance_record_id'=l.id::text)""",
    "请款单状态不一致": """SELECT count(*) FROM business_records b JOIN legacy_finance_records l ON l.id=(b.data->>'legacy_finance_record_id')::bigint WHERE b.module='contract_payment' AND b.deleted_at IS NULL AND coalesce(b.data->>'legacy_status_code','')<>l.status_code""",
    "到账": """SELECT count(*) FROM "FAM_AR_Payment" s WHERE "PaymentId" < 10000000 AND upper(coalesce("IsActived",''))='T' AND NOT EXISTS (SELECT 1 FROM incoming_payments p WHERE p.receipt_no='HZ-RCPT-'||s."PaymentId")""",
    "发票": """SELECT count(*) FROM "FAM_Invoice" s WHERE upper(coalesce(s."IsActived",'T'))='T' AND "InvoiceId" < 10000000 AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='invoice' AND b.serial_no='HZ-INV-'||s."InvoiceId")""",
    "未完成任务": """SELECT count(*) FROM "Legal_Case_Task" s WHERE "TaskId" < 10000000 AND upper(coalesce("IsActived",''))='T' AND "TaskStatus" IN (1,2) AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='task' AND b.serial_no='HZ-CT-'||s."TaskId")
        AND EXISTS (SELECT 1 FROM "Legal_Case" lc JOIN business_records bc ON bc.module='case' AND bc.serial_no=trim(lc."CaseNo") AND bc.deleted_at IS NULL WHERE lc."CaseId"=s."CaseId" AND upper(coalesce(lc."IsActived",'T'))='T')""",
    "官文收文": """SELECT count(*) FROM "FIO_Offical_MetaFile" s WHERE "FileId" < 10000000 AND upper(coalesce("IsActived",''))='T' AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='document' AND b.serial_no='HZ-FIO-'||s."FileId")
        AND EXISTS (SELECT 1 FROM business_records bc WHERE bc.module='case' AND bc.serial_no=trim(s."CaseNo") AND bc.deleted_at IS NULL)""",
}


def alignment_check(state, state_path):
    """每轮写完对一遍主要业务类：旧系统有、新系统没对应记录的条数。首轮记为基线（已说明过原因的老缺口），之后比基线多了就告警。"""
    out = {"missing": {}, "worse": {}}
    with psycopg.connect(pg_dsn()) as c:
        c.execute("SET default_transaction_read_only = on"); c.execute("SET statement_timeout = '60s'")
        for name, q_ in ALIGN_CHECKS.items():
            try:
                out["missing"][name] = c.execute(q_).fetchone()[0]
            except Exception as exc:
                c.rollback(); c.execute("SET default_transaction_read_only = on"); c.execute("SET statement_timeout = '60s'")
                out["missing"][name] = f"查询失败：{type(exc).__name__}"
    base = state.setdefault("alignment_baseline", {})
    for name, n in out["missing"].items():
        if not isinstance(n, int):
            continue
        if name not in base:
            base[name] = n
        elif n > base[name]:
            out["worse"][name] = {"baseline": base[name], "now": n}
    tmp = Path(state_path).with_suffix(".tmp"); json.dump(state, open(tmp, "w")); tmp.replace(state_path)
    return out


def build_native(cur, pg, pks):
    """起始名单：镜像表里主键不在旧库的行（新系统自己写的）。只在第一次写入前算一次，之后靠高位号和 -R 认。"""
    out = {}
    for t in NATIVE_TABLES:
        pk = pks.get(t)
        if not pk or len(pk) != 1 or pg.execute("SELECT to_regclass(%s)", (f'public."{t}"',)).fetchone()[0] is None:
            continue
        r = load_47(cur)
        while busy(r):
            time.sleep(60); r = load_47(cur)
        cur.execute(f"SELECT {q(pk[0])} FROM {q(t)} WITH (NOLOCK) OPTION (MAXDOP 1)")
        legacy = {norm(x[0]) for x in cur.fetchall()}
        app = [k for (k,) in pg.execute(f'SELECT "{pk[0]}"::text FROM "{t}"') if norm(k) not in legacy]
        if app:
            out[t] = sorted(str(k).upper() for k in app)
    tmp = NATIVE_FILE.with_suffix(".tmp"); json.dump(out, open(tmp, "w")); os.chmod(tmp, 0o600); tmp.replace(NATIVE_FILE)
    return {t: set(v) for t, v in out.items()}


def save_native_start(native):
    """提交后把起始名单里已换走的主键去掉（11-02 起）：不然下一轮重叠窗口再读到同一条旧记录，会把它当新系统行再换一次号。"""
    if not NATIVE_FILE.exists():
        return
    start = json.load(open(NATIVE_FILE))
    out = {t: [k for k in keys if k in native.get(t, set())] for t, keys in start.items()}
    if out != start:
        tmp = NATIVE_FILE.with_suffix(".tmp"); json.dump(out, open(tmp, "w")); os.chmod(tmp, 0o600); tmp.replace(NATIVE_FILE)


HELD_FILE = Path("/opt/sunhold-oa/sync-status/hz-case-delete-held.json")


def save_held_case_deletes(held):
    """老系统已删、新系统还有费用或未完成任务而先不删的案件（陶威 11-02 21:18 选 A）：写待处理清单，标出本轮新出现的，告警程序读它通知人处理。"""
    prev = {}
    if HELD_FILE.exists():
        try:
            prev = {item["case_no"]: item for item in json.load(open(HELD_FILE)).get("held", [])}
        except (ValueError, KeyError, TypeError):
            prev = {}
    now = datetime.now().isoformat(timespec="seconds")
    items = [{**item, "first_seen": prev.get(item["case_no"], {}).get("first_seen", now)} for item in held]
    new = [item["case_no"] for item in items if item["case_no"] not in prev]
    released = [no for no in prev if no not in {item["case_no"] for item in items}]
    payload = {"updated": now, "count": len(items), "new": new, "released": released, "held": items}
    HELD_FILE.parent.mkdir(mode=0o755, exist_ok=True)
    tmp = HELD_FILE.with_suffix(".tmp"); json.dump(payload, open(tmp, "w"), ensure_ascii=False, indent=1); tmp.replace(HELD_FILE)
    return {"count": len(items), "new": new, "released": released}


def write_round(args, delta, native, pks, started, state):
    sys.path.insert(0, LIB)
    os.environ.setdefault("HZ_ALIGNMENT_OUTPUT_DIR", "/opt/sunhold-oa/hz-sync/reports/align")
    import hz_live_write as w
    rw = psycopg.connect(pg_dsn(), autocommit=False)
    for s in ("SET TIME ZONE 'Asia/Shanghai'", "SET lock_timeout = '5s'", "SET statement_timeout = '10min'", "SET application_name = 'oa-hz-sync'"):
        rw.execute(s)
    committed = psycopg.connect(pg_dsn(), autocommit=True)
    committed.execute("SET TIME ZONE 'Asia/Shanghai'"); committed.execute("SET default_transaction_read_only = on")
    t0 = time.time()
    try:
        rep, backup = w.main(rw, delta, native, pks, LIB + "/align", LIB + "/repo", committed)
        BACKUP_DIR.mkdir(mode=0o700, exist_ok=True)
        bfile = BACKUP_DIR / f"hz-write-{started:%Y%m%d-%H%M%S}{'' if args.commit else '-rehearsal'}.json"
        fd = os.open(bfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            json.dump(backup, fh, ensure_ascii=False, default=w.jsonable)
        if args.commit:
            rw.commit()
        else:
            rw.rollback()
    except BaseException:
        rw.rollback()
        raise
    finally:
        rw.close(); committed.close()
    out = {"committed": args.commit, "seconds": round(time.time() - t0), "report": rep, "conflict_count": len(backup["conflicts"]),
           "conflicts": backup["conflicts"][:200], "backup": str(bfile), "created_record_ids": backup.get("business_created", [])}
    if args.commit:
        out["case_delete_held"] = save_held_case_deletes(w.HELD_CASE_DELETES)
        save_native_start(native)
        state["watermark"] = (started - OVERLAP).strftime("%Y-%m-%d %H:%M:%S")
        tmp = Path(args.state).with_suffix(".tmp"); json.dump(state, open(tmp, "w")); tmp.replace(args.state)
        if rep.get("core_customer_created") or rep.get("core_case_created") or rep.get("core_ipr_case_created"):
            out["party_library"] = rebuild_parties()
        out["ap_promotion"] = promote_ap_payments(bfile)
    return out


def promote_ap_payments(bfile):
    """旧系统新的付款申请（请款单）和付款包：用系统自带的 promote_imported_ap_payments 接入现行付款流程（它自己判重、只建没建过的）。
    建了什么记进同一轮备份旁边的 .promotion.json，回滚时一并撤。没有待接入的就不跑。"""
    with psycopg.connect(pg_dsn()) as c:
        c.execute("SET default_transaction_read_only = on")
        todo = c.execute("""SELECT count(*) FROM legacy_finance_records l WHERE l.record_kind='ap_payment' AND l.source_table='FAM_AP_Payment'
            AND NOT EXISTS (SELECT 1 FROM business_records b WHERE b.module='contract_payment' AND b.data->>'legacy_finance_record_id' = l.id::text)""").fetchone()[0]
        if not todo:
            return {"pending": 0}
        top = c.execute("SELECT max(id) FROM business_records").fetchone()[0]
        tx_top = c.execute("SELECT coalesce(max(id),0) FROM finance_transactions").fetchone()[0]
        ev_top = c.execute("SELECT coalesce(max(id),0) FROM workflow_events").fetchone()[0]
    py = sys.executable
    run = subprocess.run([py, "-B", LIB + "/scripts/promote_imported_ap_payments.py", "--apply"], capture_output=True, text=True, timeout=600,
                         cwd="/opt/sunhold-oa/runtime/enterprise/current/api")
    result = {"pending": todo, "exit": run.returncode, "output": (run.stdout or run.stderr)[-1500:]}
    # 同步 A1：账号不全照常转入的请款单、新补的收款方参数，列进每轮报告。
    try:
        summary = json.loads(run.stdout)
        result["incomplete_account"] = summary.get("incomplete_account", [])
        result["payment_type_params_created"] = summary.get("payment_type_params_created", [])
    except ValueError:
        pass
    with psycopg.connect(pg_dsn()) as c:
        c.execute("SET default_transaction_read_only = on")
        made = [r[0] for r in c.execute("SELECT id FROM business_records WHERE id > %s AND module IN ('contract_payment','finance_package') ORDER BY id", (top,))]
        side = {"business_records": made,
                "finance_transactions": [r[0] for r in c.execute("SELECT id FROM finance_transactions WHERE id > %s AND finance_record_id = ANY(%s)", (tx_top, made))],
                "workflow_events": [r[0] for r in c.execute("SELECT id FROM workflow_events WHERE id > %s AND record_id = ANY(%s)", (ev_top, made))]}
    path = Path(str(bfile).replace(".json", ".promotion.json"))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(side, fh)
    result.update({k: len(v) for k, v in side.items()})
    if run.returncode != 0:
        global FAILED_DETAIL
        FAILED_DETAIL = "付款申请接入失败：" + result["output"][-300:]
    return result


def rebuild_parties():
    """新增了客户/案件：按系统自带的当事人库重建登记当事人（同管理员“重建当事人库”）。失败只记下，不影响已提交的同步。"""
    try:
        sys.path.insert(0, "/opt/sunhold-oa/runtime/enterprise/current/api")
        from sqlalchemy import create_engine
        from app.core.party_library import rebuild_party_library
        engine = create_engine(pg_dsn().replace("postgresql://", "postgresql+psycopg://", 1))
        with engine.begin() as conn:
            return {"ok": True, "entries": rebuild_party_library(conn)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}


def write_latest(report_dir, status, started, detail=None, last_ok=None):
    """latest.json：告警程序只看这一份。lag_minutes = 现在距最近一次成功同步覆盖到的时间点。"""
    if MODE != "live":
        # 手动空跑/演算（改代码前的试跑）不碰告警状态：只有真正写入的那几轮才算“同步正常”（11-02 技术助手发现空跑把 hz.json 改成了演算）
        rehearsal = {"source": "hz", "status": status, "mode": MODE, "run_started": started.isoformat(timespec="seconds"),
                     "run_finished": datetime.now().isoformat(timespec="seconds"), "detail": detail}
        tmp = Path(report_dir) / "latest-rehearsal.tmp"; json.dump(rehearsal, open(tmp, "w"), ensure_ascii=False, indent=1)
        tmp.replace(Path(report_dir) / "latest-rehearsal.json")
        return
    path = Path(report_dir) / "latest.json"
    prev = json.load(open(path)) if path.exists() else {}
    ok_at = last_ok or prev.get("last_ok_started")
    now = datetime.now()
    latest = {"source": "hz", "status": status, "run_started": started.isoformat(timespec="seconds"),
              "run_finished": now.isoformat(timespec="seconds"), "last_ok_started": ok_at,
              "lag_minutes": round((now - datetime.fromisoformat(ok_at)).total_seconds() / 60, 1) if ok_at else None,
              "mode": MODE, "detail": detail}
    tmp = path.with_suffix(".tmp"); json.dump(latest, open(tmp, "w"), ensure_ascii=False, indent=1); tmp.replace(path)
    # 两边同步统一的告警状态文件（与分支3 的 hd.json 同格式），告警程序只读这里
    shared = Path("/opt/sunhold-oa/sync-status"); shared.mkdir(mode=0o755, exist_ok=True)
    summary = detail if status != "ok" else {"live": "写入正常", "write-rehearsal": "写入演算正常（已回滚）"}.get(MODE, "只读试跑正常")
    common = {"name": "hz", "last_run": latest["run_finished"], "last_ok": ok_at, "ok": status == "ok",
              "error": "" if status == "ok" else (detail or status)[:300], "lag_minutes": latest["lag_minutes"],
              "mode": "detect-only" if latest["mode"] == "dry-run" else latest["mode"], "summary": summary}
    tmp = shared / "hz.json.tmp"; json.dump(common, open(tmp, "w"), ensure_ascii=False); os.chmod(tmp, 0o644); tmp.replace(shared / "hz.json")


if __name__ == "__main__":
    ap0 = argparse.ArgumentParser(); ap0.add_argument("--report-dir", required=True); a0, _ = ap0.parse_known_args()
    t0 = datetime.now()
    try:
        status = main()
        write_latest(a0.report_dir, status or "ok", t0, detail=FAILED_DETAIL,
                     last_ok=t0.isoformat(timespec="seconds") if (status or "ok") == "ok" else None)
    except BaseException as exc:  # 含 SystemExit：隧道失败、47 持续繁忙等
        write_latest(a0.report_dir, "failed", t0, detail=f"{type(exc).__name__}: {exc}"[:500])
        raise
