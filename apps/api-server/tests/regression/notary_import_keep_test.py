"""公证 A（陶威 11-06）：导入过的公证书号、仓库、发票号，沪知同步写完一轮后要原样留下。"""

import importlib.util
import sys
import types
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.modules.setdefault("psycopg", types.ModuleType("psycopg"))
sys.modules.setdefault("psycopg.types", types.ModuleType("psycopg.types"))
json_module = types.ModuleType("psycopg.types.json")


class Jsonb:
    def __init__(self, obj):
        self.obj = obj


json_module.Jsonb = sys.modules.get("psycopg.types.json", types.SimpleNamespace(Jsonb=Jsonb)).Jsonb
sys.modules.setdefault("psycopg.types.json", json_module)
spec = importlib.util.spec_from_file_location("notary_import_keep", ROOT / "scripts/hz_sync/notary_import_keep.py")
keep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keep)


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakePg:
    def __init__(self, records):
        self.records = records
        self.updates = 0

    def execute(self, query, params=None):
        if query.startswith("SELECT id, data"):
            return Result([(rid, rec["data"]) for rid, rec in self.records.items() if "notary_import_fields" in rec["data"]])
        if query.startswith("SELECT data, status"):
            rec = self.records.get(params[0])
            return Result([(rec["data"], rec["status"])] if rec else [])
        self.updates += 1
        self.records[params[1]]["data"] = params[0].obj
        return Result([])


def keep_both(data, field, new_value, legacy_value, row):
    data.setdefault("legacy_sync_conflicts", []).append({"field": field, "new_value": new_value, "legacy_value": legacy_value})
    return f"{field}:{legacy_value}"


class NotaryImportKeepTest(unittest.TestCase):
    def run_round(self, data, sync_writes):
        pg = FakePg({1: {"data": data, "status": "已取证"}})
        kept = keep.snapshot(pg)
        pg.records[1]["data"] = sync_writes(dict(data))
        events, rep = [], Counter()
        keep.restore(pg, kept, keep_both, lambda _pg, rid, status, items, _rep: events.extend(items), rep)
        return pg, events, rep

    def test_sync_overwrite_is_put_back_and_legacy_value_recorded(self):
        imported = {"notary_import_fields": ["certificate_no", "warehouse"], "certificate_no": "新号", "notarization_no": "新号", "warehouse": "新仓", "shop_name": "旧店"}
        pg, events, rep = self.run_round(imported, lambda d: {**d, "notarization_no": "旧号", "warehouse": "旧仓", "shop_name": "新店"})
        data = pg.records[1]["data"]
        self.assertEqual((data["notarization_no"], data["warehouse"]), ("新号", "新仓"))
        self.assertEqual(data["shop_name"], "新店")  # 其他字段照常同步
        self.assertEqual(events, ["notarization_no:旧号", "warehouse:旧仓"])
        self.assertEqual(rep["notary_import_kept"], 1)

    def test_fields_not_imported_still_follow_legacy(self):
        imported = {"notary_import_fields": ["warehouse"], "warehouse": "新仓", "invoice_no": "旧票", "notarization_no": "旧号"}
        pg, events, _ = self.run_round(imported, lambda d: {**d, "invoice_no": "更新票", "notarization_no": "更新号"})
        self.assertEqual((pg.records[1]["data"]["invoice_no"], pg.records[1]["data"]["notarization_no"]), ("更新票", "更新号"))
        self.assertEqual((pg.updates, events), (0, []))

    def test_full_overwrite_keeps_marker_and_values(self):
        imported = {"notary_import_fields": ["invoice_no"], "invoice_no": "新票"}
        pg, _, _ = self.run_round(imported, lambda d: {"invoice_no": "旧票"})
        self.assertEqual(pg.records[1]["data"]["notary_import_fields"], ["invoice_no"])
        self.assertEqual(pg.records[1]["data"]["invoice_no"], "新票")

    def test_value_changed_on_page_after_import_is_what_gets_kept(self):
        """快照取的是本轮开始前的值：导入后页面上改过的不会被改回导入值。"""
        imported = {"notary_import_fields": ["warehouse"], "warehouse": "页面改过的仓"}
        pg, _, _ = self.run_round(imported, lambda d: {**d, "warehouse": "旧仓"})
        self.assertEqual(pg.records[1]["data"]["warehouse"], "页面改过的仓")

    def test_no_marker_is_untouched(self):
        pg = FakePg({1: {"data": {"warehouse": "旧仓"}, "status": ""}})
        self.assertEqual(keep.snapshot(pg), {})


if __name__ == "__main__":
    unittest.main()
