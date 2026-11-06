"""陶威 11-06“公证 A”：新系统导入过的公证书号、仓库、发票号，沪知同步不覆盖。

导入时在证物的 data.notary_import_fields 记下导入过哪几项。同步一轮开始前按这个标记记下当前值，
写完后把被改掉的值放回去，旧系统不同的值记进“旧系统同步记录”。记的是本轮开始前的值，所以导入后有人在页面上再改，也照样保留。
部署位置：生产 /opt/sunhold-oa/hz-sync/lib/，由 hz_live_write.main 调用；每晚全表比对走同一套写入，一并覆盖。
"""
from psycopg.types.json import Jsonb

MARKER = "notary_import_fields"
# 导入项 -> 证物 data 里存这一项的键；第一个是记录“旧系统同步记录”用的字段名。
FIELD_KEYS = {
    "certificate_no": ("certificate_no", "notarization_no", "notary_no", "notarial_no"),
    "warehouse": ("warehouse",),
    "invoice_no": ("invoice_no",),
}
LABELS = {"certificate_no": "公证书号", "warehouse": "仓库", "invoice_no": "发票号"}
_MISSING = object()


def snapshot(pg):
    """{证物 id: {"marker": 标记, "values": {键: 当前值}}}；键原本不存在的不放进 values。"""
    out = {}
    for rid, data in pg.execute(
        "SELECT id, data FROM business_records WHERE module='evidence' AND deleted_at IS NULL AND data->'notary_import_fields' IS NOT NULL"
    ).fetchall():
        marker = [field for field in (data or {}).get(MARKER) or [] if field in FIELD_KEYS]
        if marker:
            out[rid] = {"marker": data[MARKER], "values": {key: data[key] for field in marker for key in FIELD_KEYS[field] if key in data}}
    return out


def restore(pg, kept, keep_both, add_events, rep):
    """把本轮被同步改掉的导入项放回去。keep_both/add_events 用 hz_live_write 里的同名函数。"""
    for rid, item in kept.items():
        row = pg.execute("SELECT data, status FROM business_records WHERE id=%s AND deleted_at IS NULL", (rid,)).fetchone()
        if not row:
            continue
        before, status = row[0] or {}, row[1]
        data, events = dict(before), []
        for field in item["marker"]:
            keys = FIELD_KEYS.get(field, ())
            for key in keys:
                now, old = data.get(key, _MISSING), item["values"].get(key, _MISSING)
                if now == old:
                    continue
                if now not in (_MISSING, None, "") and old is not _MISSING:
                    event = keep_both(data, key, old, now, {})
                    if event:
                        events.append(event)
                if old is _MISSING:
                    data.pop(key, None)
                else:
                    data[key] = old
        data[MARKER] = item["marker"]
        if data != before:
            pg.execute("UPDATE business_records SET data=%s WHERE id=%s", (Jsonb(data), rid))
            add_events(pg, rid, status, events, rep)
            rep["notary_import_kept"] += 1
