"""HD 知识产权旧系统（139 PRD_IPR_HD_20180929）→ 新 OA 定时同步（在新生产上跑，每 15 分钟）。

对旧服务器只读：经 SSH 在 139 上以低优先级执行 sqlcmd SELECT（NOLOCK），结果流式回传、限速，139 上不落盘；
每轮先看 139 负载，忙就本轮跳过。
1. 每张业务表数 ChangeTime/CreateTime ≥ 水位线的行（提醒类表 IPR_Case_Event/_AFM 是旧系统定时任务重算的，不看）；
   HR_Staff 没有时间列，比行数和校验和。
2. 没变化：写报告、水位线前移，结束（绝大多数轮次）。
3. 有变化：把 24 张表整表只读导出成 JSONL（与 10-30 快照同格式）；新增的案件文件在 139 上用 ossutil 逐个传到
   oss://oabeifen3217/HD.IPR/HD.IPR.WEB/CaseFiles/（实例角色只写不删、低优先级，-u 已存在就跳过）；
   列出 OSS 上 HD.IPR 对象；再跑 import_ipr_hd.py（按 HD 主键幂等：客户/案件以旧系统为准更新，日志去重，附件只补新的），
   每轮一个批次号 ipr_hd_sync_<时间>，可单独回滚。
不带 --apply 时第 3 步只演练（导入整体回滚、不传文件）。
用法：hd_live_sync.py --state S --report-dir D --work-dir W --scripts-dir X [--apply]
"""
import argparse, datetime as dt, json, math, os, shutil, subprocess, sys, time
from pathlib import Path

PRIVATE = Path("/opt/sunhold-oa/private/hz-sync")
HOST = "Administrator@139.224.35.141"
DB = "PRD_IPR_HD_20180929"
TABLES = ["CRM_Customer", "CRM_Customer_Contacts", "FAM_AR_CaseFee", "FAM_AR_CaseFee_Log", "FAM_AR_PaymentType", "FAM_Invoice_File",
          "HR_Staff", "IPR_Case", "IPR_CaseFileType_CaseFeeTypeList", "IPR_CasePhase", "IPR_CaseType", "IPR_CaseType_FeeTypeList",
          "IPR_Case_AssistedFeeType", "IPR_Case_Customer", "IPR_Case_Customer_Contacts", "IPR_Case_Event", "IPR_Case_Event_AFM",
          "IPR_Case_Event_NotIn", "IPR_Case_FeeType", "IPR_Case_File", "IPR_Case_FileType", "IPR_Case_Log", "IPR_Case_Monitoring",
          "IPR_Case_ReminderType"]
IGNORE_CHANGES = {"IPR_Case_Event", "IPR_Case_Event_AFM"}  # 旧系统定时任务每天重算，新系统不用
HR_KEEP = ["StaffId", "StaffGuid", "StaffNo", "StaffName", "StaffChName", "DepartmentId", "IsActived", "JobStatus"]
EXCLUDE_CASES = "HDFL1000221,HDLaw1910171"  # 10-31 首次导入时陶威定不导的两件
OSS_TARGET = "oss://oabeifen3217/HD.IPR/HD.IPR.WEB/CaseFiles/CaseFiles/"
LOCAL_ROOT = "G:/HD.IPR/HD.IPR.WEB/CaseFiles/CaseFiles/"
OSSUTIL = r"F:\OSS-Transfer-Tools\ossutil-2.4.0-windows-amd64-go1.20\ossutil.exe"
OVERLAP = dt.timedelta(minutes=10)
RATE = 150 * 1024  # 回传限速（字节/秒）
BATCH = 20000
BUSY_CPU, MIN_FREE_MB = 70, 1500


def ssh_cmd(remote: str) -> list[str]:
    return ["ssh", "-n", "-C", "-i", str(PRIVATE / "legacy139_ed25519"), "-o", "IdentitiesOnly=yes",
            "-o", f"UserKnownHostsFile={PRIVATE / 'known_hosts'}", "-o", "StrictHostKeyChecking=yes", "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=30", HOST, remote]


def remote_raw(cmd: str, timeout=900) -> str:
    p = subprocess.Popen(ssh_cmd(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    buf, t0, got = bytearray(), time.time(), 0
    while True:
        chunk = p.stdout.read(16384)
        if not chunk:
            break
        buf += chunk; got += len(chunk)
        ahead = got / RATE - (time.time() - t0)
        if ahead > 0:
            time.sleep(ahead)
    err = p.stderr.read().decode("gb18030", "replace")
    if p.wait(timeout=timeout) != 0:
        raise RuntimeError(f"139 执行失败：{err[:300]} {bytes(buf[:300]).decode('gb18030', 'replace')}")
    return bytes(buf).decode("gb18030")


def sql(query: str, timeout=900) -> list[str]:
    assert '"' not in query and "%" not in query and "^" not in query
    out = remote_raw(f'start "" /low /b /wait sqlcmd -E -S . -d {DB} -h -1 -y 0 -b -l 10 -t {timeout} -Q "SET NOCOUNT ON;{query}"', timeout)
    return [line for line in out.split("\r\n")]


def load_139() -> dict:
    out = remote_raw("wmic cpu get loadpercentage /value & wmic os get FreePhysicalMemory /value", 60)
    vals = dict(l.strip().split("=", 1) for l in out.splitlines() if "=" in l and l.strip())
    return {"cpu": int(vals.get("LoadPercentage", 100) or 100), "free_mb": int(vals.get("FreePhysicalMemory", 0) or 0) // 1024}


def meta() -> dict[str, list[dict]]:
    names = ",".join(f"'{t}'" for t in TABLES)
    rows = sql("SELECT t.name+'|'+CAST(c.column_id AS varchar(10))+'|'+c.name+'|'+y.name+'|'+CAST(c.max_length AS varchar(10))+'|'"
               "+CAST(c.precision AS varchar(10))+'|'+CAST(c.scale AS varchar(10))+'|'+CAST(c.is_identity AS varchar(1))+'|'"
               "+CAST(ISNULL(ic.key_ordinal,0) AS varchar(5)) FROM sys.tables t JOIN sys.columns c ON c.object_id=t.object_id "
               "JOIN sys.types y ON y.user_type_id=c.user_type_id LEFT JOIN sys.indexes i ON i.object_id=t.object_id AND i.is_primary_key=1 "
               "LEFT JOIN sys.index_columns ic ON ic.object_id=t.object_id AND ic.index_id=i.index_id AND ic.column_id=c.column_id "
               f"WHERE t.name IN ({names}) ORDER BY t.name, c.column_id", 120)
    tables: dict[str, list[dict]] = {}
    for line in rows:
        f = line.strip().split("|")
        if len(f) != 9:
            continue
        t, cid, name, typ, ml, prec, scale, ident, pk = f
        if t == "HR_Staff" and name not in HR_KEEP:
            continue
        tables.setdefault(t, []).append({"id": int(cid), "name": name, "type": typ, "ml": int(ml), "prec": int(prec),
                                          "scale": int(scale), "ident": ident == "1", "pk": int(pk)})
    missing = set(TABLES) - set(tables)
    if missing:
        raise RuntimeError(f"139 上缺表：{sorted(missing)}")
    return tables


def changed_counts(tables: dict, since: str) -> dict:
    counts = {}
    for t, cols in tables.items():
        names = {c["name"] for c in cols}
        tc = [c for c in ("ChangeTime", "CreateTime") if c in names]
        if t in IGNORE_CHANGES or not tc:
            continue
        cond = " OR ".join(f"[{c}]>='{since}'" for c in tc)
        line = next((l.strip() for l in sql(f"SELECT CAST(COUNT(*) AS varchar(10)) FROM [{t}] WITH (NOLOCK) WHERE {cond}", 120) if l.strip()), "0")
        counts[t] = int(line)
    return counts


def hr_signature(tables: dict) -> str:
    cols = ",".join(f"[{c['name']}]" for c in tables["HR_Staff"])
    return next((l.strip() for l in sql(f"SELECT CAST(COUNT(*) AS varchar(10))+'/'+CAST(CHECKSUM_AGG(BINARY_CHECKSUM({cols})) AS varchar(20)) FROM HR_Staff WITH (NOLOCK)", 120) if l.strip()), "")


def unescape(v: str):
    if v == "\\N":
        return None
    if "\\" not in v:
        return v
    out, i, m = [], 0, {"\\": "\\", "p": "|", "r": "\r", "n": "\n", "t": "\t"}
    while i < len(v):
        if v[i] == "\\" and i + 1 < len(v) and v[i + 1] in m:
            out.append(m[v[i + 1]]); i += 2
        else:
            out.append(v[i]); i += 1
    return "".join(out)


def typed(v, typ: str):
    """转成与 10-30 快照 JSONL 相同的写法：整数为数字、bit 为布尔、decimal 为字符串、日期为 ISO、GUID 大写。"""
    if v is None:
        return None
    if typ in ("int", "bigint", "smallint", "tinyint"):
        return int(v)
    if typ == "bit":
        return v.strip() == "1"
    if typ in ("float", "real"):
        return float(v)
    if typ in ("datetime", "smalldatetime", "datetime2", "date"):
        stamp = dt.datetime.fromisoformat(v.strip())
        return stamp.isoformat(timespec="milliseconds") if stamp.microsecond else stamp.isoformat(timespec="seconds")
    if typ == "uniqueidentifier":
        return v.strip().upper()
    return v


def export_sql(t: str, cols: list[dict], where: str) -> str:
    ids = ",".join(str(c["id"]) for c in cols)
    pkcols = [c["name"] for c in sorted((c for c in cols if c["pk"]), key=lambda c: c["pk"])] or [cols[0]["name"]]
    order = ",".join(f"[{n}]" for n in pkcols)
    bs = "CHAR(92)"
    esc = (f"'ISNULL(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(['+c.name+'],{bs},{bs}+{bs}),CHAR(124),{bs}+''p''),"
           f"CHAR(13),{bs}+''r''),CHAR(10),{bs}+''n''),CHAR(9),{bs}+''t''),{bs}+''N'')'")
    return ("DECLARE @e varchar(max);SET @e='';"
            "SELECT @e=@e+'+''|''+'+CASE WHEN y.name IN ('char','varchar','nvarchar','nchar','text','ntext') THEN " + esc +
            f" WHEN y.name='datetime' THEN 'ISNULL(CONVERT(varchar(23),['+c.name+'],121),{bs}+''N'')'"
            f" ELSE 'ISNULL(CONVERT(varchar(60),['+c.name+']),{bs}+''N'')' END"
            f" FROM sys.columns c JOIN sys.types y ON y.user_type_id=c.user_type_id"
            f" WHERE c.object_id=OBJECT_ID('{t}') AND c.column_id IN ({ids}) ORDER BY c.column_id;"
            "SET @e=STUFF(@e,1,5,'');"
            f"EXEC('SELECT CAST('''' AS varchar(max))+'+@e+'+''|~'' FROM [{t}] WITH (NOLOCK) WHERE {where} ORDER BY {order}')")


def export_all(tables: dict, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for t, cols in sorted(tables.items()):
        total = int(next(l.strip() for l in sql(f"SELECT CAST(COUNT(*) AS varchar(20)) FROM [{t}] WITH (NOLOCK)", 120) if l.strip()))
        ranges = ["1=1"]
        pkc = [c for c in cols if c["pk"]]
        if len(pkc) == 1 and pkc[0]["type"] in ("int", "bigint") and total > BATCH:
            n = pkc[0]["name"]
            lo, hi = map(int, next(l.strip() for l in sql(
                f"SELECT CAST(MIN([{n}]) AS varchar(20))+','+CAST(MAX([{n}]) AS varchar(20)) FROM [{t}] WITH (NOLOCK)", 120) if l.strip()).split(","))
            step = math.ceil((hi - lo + 1) / math.ceil(total / BATCH))
            ranges = [f"[{n}] BETWEEN {a} AND {min(a + step - 1, hi)}" for a in range(lo, hi + 1, step)]
        written = 0
        with open(out / f"{t}.jsonl", "w", encoding="utf-8") as fh:
            for w in ranges:
                for line in sql(export_sql(t, cols, w)):
                    s = line.rstrip(" ")
                    if not s:
                        continue
                    if not s.endswith("|~"):
                        raise RuntimeError(f"{t} 行被截断：{s[:80]!r}")
                    vals = s[:-2].split("|")
                    if len(vals) != len(cols):
                        raise RuntimeError(f"{t} 列数 {len(vals)} != {len(cols)}")
                    fh.write(json.dumps({c["name"]: typed(unescape(v), c["type"]) for c, v in zip(cols, vals)}, ensure_ascii=False) + "\n")
                    written += 1
                time.sleep(2)
        counts[t] = {"rows": written, "source_rows": total, "match": written == total}
        if written != total:
            raise RuntimeError(f"{t} 导出 {written} 行，源库 {total} 行，不一致（可能导出期间有改动），本轮放弃")
    schema = {t: [[c["name"], c["type"]] for c in cols] for t, cols in tables.items()}
    (out / "_schema.json").write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    (out / "_counts.json").write_text(json.dumps({"source": f"139 {DB}（只读流式读取）", "exported_at": dt.datetime.now().isoformat(timespec="seconds"),
                                                   "tables": counts}, ensure_ascii=False), encoding="utf-8")
    return counts


def new_case_files(out: Path, since: str) -> list[dict]:
    rows = []
    for line in open(out / "IPR_Case_File.jsonl", encoding="utf-8"):
        r = json.loads(line)
        stamp = r.get("CreateTime") or r.get("UploadingTime") or ""
        if str(r.get("Actived") or "").upper() == "T" and stamp and stamp.replace("T", " ") >= since and r.get("CaseNo") and r.get("FullPath"):
            rows.append({"case_no": r["CaseNo"], "name": r["FullPath"].strip(), "file_id": r.get("FileId")})
    return rows


def upload_files(files: list[dict]) -> dict:
    """在 139 上逐个 ossutil cp -u：实例角色只写不删、低优先级；源文件只读；不在 139 写日志或临时文件。"""
    done, failed = 0, []
    for f in files:
        if any(ch in f["name"] + f["case_no"] for ch in '"%^&|<>'):
            failed.append({**f, "error": "文件名含特殊字符，跳过"}); continue
        src, dst = f"{LOCAL_ROOT}{f['case_no']}/{f['name']}", f"{OSS_TARGET}{f['case_no']}/{f['name']}"
        cmd = (f'start "" /low /b /wait "{OSSUTIL}" cp -u "{src}" "{dst}" --mode EcsRamRole --endpoint oss-cn-shanghai-internal.aliyuncs.com '
               f'--region cn-shanghai --no-progress -f')
        try:
            remote_raw(cmd, 600); done += 1
        except RuntimeError as exc:
            failed.append({**f, "error": str(exc)[:200]})
        time.sleep(1)
    return {"uploaded": done, "failed": failed}


def list_oss(out: Path) -> int:
    script = ("import base64,hashlib,hmac,re,httpx,json\nfrom email.utils import formatdate\nfrom html import unescape\n"
              "from app.core.oss_attachments import _load_credentials,_endpoint_host\nak,sk=_load_credentials();_,host=_endpoint_host()\n"
              "marker,n='',0\nwith httpx.Client(timeout=60) as cli:\n while True:\n  d=formatdate(usegmt=True)\n"
              "  sig=base64.b64encode(hmac.new(sk.encode(),f'GET\\n\\n\\n{d}\\n/oabeifen3217/'.encode(),hashlib.sha1).digest()).decode()\n"
              "  p={'prefix':'HD.IPR/HD.IPR.WEB/CaseFiles/CaseFiles/','max-keys':1000}\n  p.update({'marker':marker} if marker else {})\n"
              "  r=cli.get(f'https://oabeifen3217.{host}/',params=p,headers={'Date':d,'Authorization':f'OSS {ak}:{sig}'});r.raise_for_status()\n"
              "  ks=re.findall(r'<Key>(.*?)</Key>\\s*<LastModified>.*?</LastModified>\\s*<ETag>(.*?)</ETag>.*?<Size>(\\d+)</Size>',r.text,re.S)\n"
              "  for k,e,s in ks: print(json.dumps([unescape(k),unescape(e),int(s)],ensure_ascii=False)); n+=1\n"
              "  if '<IsTruncated>true' not in r.text or not ks: break\n  marker=unescape(ks[-1][0])\n")
    api = "/opt/sunhold-oa/runtime/enterprise/current/api"
    with open(out / "oss_keys.jsonl", "w", encoding="utf-8") as fh:
        subprocess.run(["bash", "-c", f"set -a; . /opt/sunhold-oa/private/production-native.env >/dev/null 2>&1; set +a; "
                        f"export OSS_CREDENTIALS_FILE=/opt/sunhold-oa/private/oss-attachment-reader.csv; cd {api} && {sys.executable} -"],
                       input=script, text=True, stdout=fh, check=True, timeout=1800)
    return sum(1 for _ in open(out / "oss_keys.jsonl", encoding="utf-8"))


def run_import(out: Path, scripts: Path, batch: str, apply: bool) -> dict:
    report = out / "import-report.json"
    cmd = [sys.executable, "-B", str(scripts / "import_ipr_hd.py"), "--source", str(out), "--oss-keys", str(out / "oss_keys.jsonl"),
           "--exclude-case-no", EXCLUDE_CASES, "--batch", batch, "--report", str(report)] + (["--apply"] if apply else [])
    env_line = ('set -a; . /opt/sunhold-oa/private/production-native.env >/dev/null 2>&1; set +a; '
                'export HD_POSTGRES_DSN=$(printf %s "$DATABASE_URL" | sed -e "s#postgresql+asyncpg://#postgresql://#" -e "s#postgresql+psycopg://#postgresql://#"); '
                'exec "$@" > "$LOG" 2>&1')
    subprocess.run(["bash", "-c", env_line, "_", *cmd], check=True, timeout=3600, env={**os.environ, "LOG": str(out / "import.log")})
    return json.loads(report.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--report-dir", required=True)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--scripts-dir", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--detect-only", action="store_true", help="只读试跑：只数变化、写报告，不导出不导入")
    ap.add_argument("--since", help="只用于补同步：覆盖水位线")
    args = ap.parse_args()
    state = json.load(open(args.state)) if os.path.exists(args.state) else {"watermark": "2026-10-30 19:00:00"}
    started = dt.datetime.now()
    wm = args.since or state["watermark"]
    since = (dt.datetime.fromisoformat(wm) - OVERLAP).strftime("%Y-%m-%d %H:%M:%S")
    report = {"started": started.isoformat(timespec="seconds"), "watermark": wm, "since": since,
              "mode": "apply" if args.apply else "detect-only" if args.detect_only else "dry-run"}
    try:
        report["load_139"] = load_139()
        if report["load_139"]["cpu"] >= BUSY_CPU or report["load_139"]["free_mb"] < MIN_FREE_MB:
            report["skipped"] = "139 繁忙，本轮跳过"
        else:
            tables = meta()
            report["changed"] = changed_counts(tables, since)
            hr = hr_signature(tables)
            report["hr_staff_changed"] = bool(state.get("hr_signature")) and hr != state.get("hr_signature")
            if sum(report["changed"].values()) == 0 and not report["hr_staff_changed"]:
                report["result"] = "无变化"
            elif args.detect_only:
                report["result"] = "有变化（只读试跑，未导出未写入；水位线不前移）"
            else:
                out = Path(args.work_dir) / f"{started:%Y%m%d-%H%M}"
                report["export"] = export_all(tables, out)
                files = new_case_files(out, since)
                report["new_files"] = len(files)
                if files and args.apply:
                    report["upload"] = upload_files(files)
                report["oss_objects"] = list_oss(out)
                batch = f"ipr_hd_sync_{started:%Y%m%d%H%M}"
                imported = run_import(out, Path(args.scripts_dir), batch, args.apply)
                report["import"] = {"batch": batch, "counts": imported.get("counts"), "case_serial_conflicts": imported.get("case_serial_conflicts"),
                                    "files_missing_in_oss": (imported.get("files_missing_in_oss") or [])[:50]}
                report["result"] = "已写入" if args.apply else "演练（未写入）"
                if args.apply:
                    shutil.rmtree(out)  # 导出含个人信息，写入后删除；固定在 work-dir 下
            if args.apply or report.get("result") == "无变化":
                state = {"watermark": started.strftime("%Y-%m-%d %H:%M:%S"), "hr_signature": hr, "last_ok": started.isoformat(timespec="seconds")}
                json.dump(state, open(args.state, "w"))
    except Exception as exc:  # noqa: BLE001 - 报告里记原因，下一轮重试；超时告警看 last_ok
        report["error"] = f"{type(exc).__name__}: {exc}"[:800]
    report["finished"] = dt.datetime.now().isoformat(timespec="seconds")
    last_ok = state.get("last_ok")
    report["lag_minutes"] = round((dt.datetime.now() - dt.datetime.fromisoformat(last_ok)).total_seconds() / 60) if last_ok else None
    Path(args.report_dir).mkdir(parents=True, exist_ok=True)
    out_file = Path(args.report_dir) / f"hd-sync-{started:%Y%m%d-%H%M}.json"
    json.dump(report, open(out_file, "w"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: report.get(k) for k in ("result", "skipped", "error", "changed", "new_files", "lag_minutes", "load_139")}, ensure_ascii=False))
    sys.exit(1 if report.get("error") else 0)


if __name__ == "__main__":
    main()
