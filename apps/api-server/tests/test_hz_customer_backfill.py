"""沪知快照导入：客户类型、已回收状态、联系人的补齐与对账必须有可重复的验证。"""

import importlib.util
import sys
import types
import unittest
from collections import Counter
from pathlib import Path

try:
    import psycopg  # noqa: F401
except ImportError:  # pragma: no cover - 无 psycopg 的环境不运行该脚本测试
    psycopg = None


SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def load_importer():
    sys.modules.setdefault("pyodbc", types.ModuleType("pyodbc"))
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("import_hz_snapshot_under_test", SCRIPTS / "import_hz_snapshot.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


class FakeCursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakePg:
    """只实现导入客户路径用到的四条 SQL，记录写入而不连接数据库。"""

    def __init__(self, records=None):
        self.records = dict(records or {})  # serial_no -> {"id", "module", "status", "data"}
        self.updates = []
        self.next_id = 1000

    def execute(self, sql, params=()):
        if sql.startswith("SELECT id, module, data FROM business_records WHERE serial_no"):
            record = self.records.get(params[0])
            return FakeCursor((record["id"], record["module"], record["data"]) if record else None)
        if sql.lstrip().startswith("INSERT INTO business_records"):
            module, serial, _title, _customer, status, payload = params[:6]
            self.next_id += 1
            self.records[serial] = {"id": self.next_id, "module": module, "status": status, "data": dict(payload.obj)}
            return FakeCursor((self.next_id,))
        if sql.startswith("SELECT status, data FROM business_records WHERE id"):
            record = next(item for item in self.records.values() if item["id"] == params[0])
            return FakeCursor((record["status"], record["data"]))
        if sql.startswith("SELECT data FROM business_records WHERE id"):
            record = next(item for item in self.records.values() if item["id"] == params[0])
            return FakeCursor((record["data"],))
        if sql.startswith("UPDATE business_records SET data = %s WHERE id"):
            payload, record_id = params
            record = next(item for item in self.records.values() if item["id"] == record_id)
            record["data"] = dict(payload.obj)
            self.updates.append(record_id)
            return FakeCursor()
        if sql.lstrip().startswith("INSERT INTO contract_objects"):
            return FakeCursor()
        if sql.startswith("UPDATE business_records SET data"):
            payload, status, record_id = params
            record = next(item for item in self.records.values() if item["id"] == record_id)
            record["data"], record["status"] = dict(payload.obj), status
            self.updates.append(record_id)
            return FakeCursor()
        raise AssertionError(f"测试未预期的 SQL: {sql[:60]}")


def customer_row(no, customer_type, active="T", customer_id=1):
    return {"CustomerId": customer_id, "CustomerNo": no, "CustomerName": f"客户{no}", "CustomerType": customer_type, "IsActived": active}


def contact_row(contact_id, customer_no, **extra):
    row = {"ContactsId": contact_id, "CustomerNo": customer_no, "Contacts": " 张三 ", "Mobilephone": "13800000000", "IsDefault": "T"}
    row.update(extra)
    return row


def empty_tables(customers, contacts):
    names = ("CRM_Customer", "CRM_Customer_Contacts", "FCM_Contract", "Legal_Case", "Legal_Case_Participant", "Legal_Investigation",
             "Legal_Investigation_Task", "Legal_Investigation_Clue", "Legal_Investigation_Clue_Evidence", "IPR_Case", "IPR_CaseType")
    tables = {name: [] for name in names}
    tables["CRM_Customer"], tables["CRM_Customer_Contacts"] = customers, contacts
    return tables


@unittest.skipIf(psycopg is None, "需要 psycopg")
class HzCustomerBackfillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hz = load_importer()

    def test_contact_table_schema_check_covers_every_column_the_mapping_reads(self):
        required = self.hz.SOURCE_COLUMNS["CRM_Customer_Contacts"]
        for column in ("Contacts", "Mobilephone", "IsDefault", "IsActived", "IsContacted", "IM"):
            self.assertIn(column, required)

    def test_new_import_writes_type_status_and_stripped_contacts(self):
        pg = FakePg()
        tables = empty_tables([customer_row("C1", 1), customer_row("C2", 2, active="F", customer_id=2)], [contact_row(7, "C1")])
        report = self.hz.import_data(pg, tables)
        first, second = pg.records["C1"], pg.records["C2"]
        self.assertEqual(first["data"]["customer_type"], "客户")
        self.assertEqual(second["data"]["customer_type"], "当事人")
        self.assertEqual((first["status"], second["status"]), ("历史数据", "已回收"))
        self.assertEqual(first["data"]["contacts"][0]["name"], "张三")
        self.assertTrue(first["data"]["contacts"][0]["is_primary"])
        self.assertEqual(report["customer_created"], 2)
        self.assertEqual(report["customer_backfilled"], 0)

    def test_existing_records_with_legacy_numeric_type_are_backfilled_once(self):
        old = {"migration_source": self.hz.SOURCE, "legacy_record": {"CustomerId": 1}, "customer_type": 1, "contacts": []}
        pg = FakePg({"C1": {"id": 5, "module": "customer", "status": "历史数据", "data": dict(old)}})
        tables = empty_tables([customer_row("C1", 1, active="F")], [contact_row(7, "C1")])
        report = self.hz.import_data(pg, tables)
        data = pg.records["C1"]["data"]
        self.assertEqual((data["customer_type"], data["legacy_customer_type"]), ("客户", 1))
        self.assertEqual(len(data["contacts"]), 1)
        self.assertEqual(pg.records["C1"]["status"], "已回收")
        self.assertEqual(report["customer_backfilled"], 1)
        again = self.hz.import_data(pg, tables)
        self.assertEqual(again["customer_backfilled"], 0)
        self.assertEqual(len(pg.updates), 1)

    def test_backfill_keeps_values_changed_on_the_page(self):
        edited = {"migration_source": self.hz.SOURCE, "legacy_record": {"CustomerId": 1}, "customer_type": "当事人",
                  "contacts": [{"id": "page-1", "name": "页面新增"}]}
        pg = FakePg({"C1": {"id": 5, "module": "customer", "status": "正常", "data": dict(edited)}})
        report = self.hz.import_data(pg, empty_tables([customer_row("C1", 1, active="F")], [contact_row(7, "C1")]))
        self.assertEqual(pg.records["C1"]["data"], edited)
        self.assertEqual(pg.records["C1"]["status"], "正常")
        self.assertEqual(report["customer_backfilled"], 0)
        self.assertEqual(pg.updates, [])

    def test_contacts_without_a_customer_are_counted(self):
        pg = FakePg()
        tables = empty_tables([customer_row("C1", 1)], [contact_row(1, "C1"), contact_row(2, ""), contact_row(3, "MISSING")])
        report = self.hz.import_data(pg, tables)
        self.assertEqual(report["customer_contact_unresolved"], 2)
        self.assertEqual(len(pg.records["C1"]["data"]["contacts"]), 1)


def contract_row(no, customer_no):
    return {"ContractId": 9, "ContractNo": no, "ContractName": "合同", "CustomerNo": customer_no}


def case_row(no, customer_no, contract_no):
    return {"CaseId": 20, "CaseNo": no, "CaseName": "案件", "CustomerNo": customer_no, "ContractNo": contract_no, "CaseTypeId": 110, "CasePhaseId": 1}


@unittest.skipIf(psycopg is None, "需要 psycopg")
class HzPageKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hz = load_importer()

    def tables_with_case(self):
        tables = empty_tables([customer_row("C1", 1)], [])
        tables["FCM_Contract"] = [contract_row("K1", "C1")]
        tables["Legal_Case"] = [case_row("A1", "C1", "K1")]
        tables["Legal_Case_Participant"] = [
            {"CaseNo": "A1", "StaffName": "lawyer2", "SortingIndex": 2},
            {"CaseNo": "A1", "StaffName": "lawyer1", "SortingIndex": 1},
            {"CaseNo": "A1", "StaffName": " ", "SortingIndex": 3},
        ]
        return tables

    def test_new_case_gets_participants_in_legacy_order(self):
        pg = FakePg()
        self.hz.import_data(pg, self.tables_with_case())
        names = [item["staff_name"] for item in pg.records["A1"]["data"]["legacy_participants"]]
        self.assertEqual(names, ["lawyer1", "lawyer2"])

    def test_existing_case_without_participants_is_filled_once(self):
        pg = FakePg()
        tables = self.tables_with_case()
        self.hz.import_data(pg, tables)
        pg.records["A1"]["data"].pop("legacy_participants")
        report = self.hz.import_data(pg, tables)
        self.assertEqual(report["case_page_keys_filled"], 1)
        self.assertEqual(len(pg.records["A1"]["data"]["legacy_participants"]), 2)
        self.assertEqual(self.hz.import_data(pg, tables)["case_page_keys_filled"], 0)

    def test_existing_case_keeps_participants_changed_on_the_page(self):
        pg = FakePg()
        tables = self.tables_with_case()
        self.hz.import_data(pg, tables)
        edited = [{"staff_name": "page-added"}]
        pg.records["A1"]["data"]["legacy_participants"] = edited
        self.hz.import_data(pg, tables)
        self.assertEqual(pg.records["A1"]["data"]["legacy_participants"], edited)

    def test_customer_and_clue_fall_back_to_the_columns_the_old_system_filled(self):
        from hz_field_maps import mapped_data
        customer = mapped_data("customer", {"CustomerType": 1, "City": "上海", "ContactAddress": "联系地址", "RegistrationCity": "", "RegistrationAddress": None})
        self.assertEqual((customer["registration_region"], customer["registered_address"]), ("上海", "联系地址"))
        clue = mapped_data("clue", {"HasProduct": "T", "Address": "", "LocationAddress": "店铺地址"})
        self.assertEqual((clue["address"], clue["product"]), ("店铺地址", True))


if __name__ == "__main__":
    unittest.main()
