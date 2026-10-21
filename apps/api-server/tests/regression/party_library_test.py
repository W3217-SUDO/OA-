"""当事人中心：我方/对方、诉讼地位推断、案件类型分类与范围；客户不进当事人库。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm.router import list_party_library
from app.core.party_library import build_entries, case_category, case_party_layout, next_party_no, rebuild_party_library
from app.database import Base
from app.core.crm import _next_party_serial_no
from app.models import BusinessRecord, IprCaseCustomer, PartyRecord, User

ADMIN = {"username": "admin", "role": "admin", "_page_menu_capability": True}


def case(customer, **data):
    return {"id": 1, "serial_no": "CODEX-PL-1", "customer": customer, "data": data}


class PartyLibraryLayoutTest(unittest.TestCase):
    def test_client_in_plaintiffs_is_plaintiff_side_and_opponent_is_defendants(self):
        layout = case_party_layout(case("甲", plaintiff="甲,乙", defendant="丙,丁", opponent="丙,丁"))
        self.assertEqual((layout["our_position"], layout["ours"], layout["theirs"], layout["their_position"]),
                         ("原告", ["甲", "乙"], ["丙", "丁"], "被告"))

    def test_client_in_defendants_swaps_sides(self):
        layout = case_party_layout(case("丙", plaintiff="甲", defendant="丙"))
        self.assertEqual((layout["our_position"], layout["ours"], layout["theirs"]), ("被告", ["丙"], ["甲"]))

    def test_explicit_client_position_wins_and_list_fields_are_supported(self):
        layout = case_party_layout(case("甲", client_position="原告/申请人", plaintiffs=["甲"], defendants=[{"name": "乙"}]))
        self.assertEqual((layout["our_position"], layout["theirs"]), ("原告", ["乙"]))

    def test_client_not_listed_is_assumed_on_the_plaintiff_side(self):
        layout = case_party_layout(case("关联公司", plaintiff="原告公司", defendant="被告公司"))
        self.assertEqual((layout["our_position"], layout["ours"], layout["theirs"]), ("原告", ["关联公司", "原告公司"], ["被告公司"]))

    def test_clients_are_not_entries_but_stay_in_the_our_side_column(self):
        rows = build_entries(case("甲", plaintiff="甲,乙", defendant="丙"), {"丙"}, ["u1"])
        self.assertEqual({r["subject_name"]: r["subject_type"] for r in rows}, {"乙": "当事人"})
        self.assertEqual(rows[0]["our_parties"], ["甲", "乙"])
        self.assertEqual(rows[0]["manager_key"], "|u1|")

    def test_client_matching_ignores_full_width_and_case_differences(self):
        rows = build_entries(case("ＡＢＣ公司", plaintiff="ＡＢＣ公司,乙", defendant="丙"), {"abc公司"}, [])
        self.assertEqual([r["subject_name"] for r in rows], ["乙", "丙"])  # 全角名字的客户同样不进库

    def test_party_number_is_the_existing_record_serial_or_blank(self):
        records = {"乙": (5, "HZKH2610001", 7)}
        rows = {r["subject_name"]: r for r in build_entries(case("甲", plaintiff="甲", defendant="乙,丙"), set(), [], records)}
        self.assertEqual((rows["乙"]["party_id"], rows["乙"]["party_no"], rows["乙"]["customer_record_id"]), (5, "HZKH2610001", 7))
        self.assertEqual((rows["丙"]["party_id"], rows["丙"]["party_no"], rows["丙"]["customer_record_id"]), (None, "", None))

    def test_arbitration_uses_applicant_titles_and_keeps_third_party(self):
        rows = build_entries(case("甲", case_type="仲裁", plaintiff="甲,戊", defendant="乙", third_parties=["丙"]), set(), [])
        by_name = {r["subject_name"]: r for r in rows}
        self.assertEqual((by_name["戊"]["subject_position"], by_name["戊"]["our_position"]), ("申请人", "申请人"))
        self.assertEqual((by_name["乙"]["subject_position"], by_name["乙"]["opponent_position"]), ("被申请人", "被申请人"))
        civil = build_entries(case("甲", case_type="民事争议", plaintiff="甲,戊", defendant="乙"), set(), [])
        self.assertEqual({r["subject_position"] for r in civil}, {"原告", "被告"})

    def test_third_party_client_stays_third_party_in_arbitration(self):
        rows = build_entries(case("丙", case_type="仲裁", plaintiff="甲", defendant="乙", third_parties=["丙"]), set(), [])
        self.assertEqual({r["subject_name"]: r["subject_position"] for r in rows}, {"甲": "申请人", "乙": "被申请人"})
        self.assertEqual(rows[0]["our_position"], "第三人")

    def test_third_party_other_than_the_client_gets_its_own_row_with_third_position(self):
        rows = {r["subject_name"]: r for r in build_entries(case("甲", plaintiff="甲", defendant="乙", third_parties=["丙"]), set(), [])}
        self.assertEqual({n: r["subject_position"] for n, r in rows.items()}, {"乙": "被告", "丙": "第三人"})
        self.assertEqual(rows["丙"]["our_position"], "原告")

    def test_representing_the_third_party_shows_third_as_our_position_and_both_opponents(self):
        rows = {r["subject_name"]: r for r in build_entries(
            case("张", case_type="行政案件及国家赔偿", plaintiff="公司", defendant="某局", third_parties=["张"]), set(), [])}
        self.assertEqual({n: r["subject_position"] for n, r in rows.items()}, {"公司": "原告", "某局": "被告"})
        self.assertEqual((rows["公司"]["our_position"], rows["公司"]["our_parties"], rows["公司"]["opponent_position"]),
                         ("第三人", ["张"], "原告/被告"))

    def test_new_party_numbers_use_dsr_prefix_year_and_five_digits_counted_separately(self):
        from datetime import datetime
        yy = f"{datetime.now():%y}"
        self.assertEqual(next_party_no([]), f"DSR{yy}00001")
        self.assertEqual(next_party_no([f"DSR{yy}00007", f"SHKH{yy}00099", "HZKH2610001"]), f"DSR{yy}00008")  # 客户编号不影响当事人流水

    def test_case_without_parties_or_client_has_no_entries(self):
        self.assertEqual(build_entries(case(""), set(), []), [])

    def test_case_types_map_to_four_categories_and_the_rest_is_other(self):
        self.assertEqual([case_category(v) for v in ("民事争议", "民事案件", "行政案件及国家赔偿", "刑事案件", "仲裁", "法律顾问", "", None)],
                         ["民事", "民事", "行政", "刑事", "仲裁", "法律顾问", "其他", "其他"])


class PartyLibraryQueryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理者", role="admin", role_ids=["admin"], password_hash="x"),
                User(username="u1", display_name="员工甲", department="一部", role="user", role_ids=["user"], password_hash="x"),
                User(username="u2", display_name="员工乙", department="一部", role="user", role_ids=["user"], password_hash="x"),
                User(username="u3", display_name="员工丙", department="二部", role="user", role_ids=["user"], password_hash="x"),
            ])
            customer = BusinessRecord(module="customer", serial_no="CODEX-PL-C1", title="甲", customer="", status="正常", owner="u1",
                                      data={"customer_type": "客户", "customer_managers": ["u1"]})
            db.add(customer)
            await db.flush()
            db.add_all([
                BusinessRecord(module="case", serial_no="CODEX-PL-A1", title="案", customer="甲", status="文书准备", owner="admin",
                               data={"plaintiff": "甲", "defendant": "乙,丙", "customer_id": customer.id}),
                BusinessRecord(module="case", serial_no="CODEX-PL-A2", title="删", customer="甲", status="已删除", owner="admin",
                               data={"plaintiff": "甲", "defendant": "丁", "customer_id": customer.id}),
            ])
            await db.commit()
            await db.run_sync(lambda session: rebuild_party_library(session.connection()))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _rebuild(self):
        async with self.sessions() as db:
            await db.run_sync(lambda session: rebuild_party_library(session.connection()))
            await db.commit()

    async def _list(self, **params):
        async with self.sessions() as db:
            args = dict(scope="company", case_no="", name="", case_category="", page=1, page_size=15, identity=ADMIN, db=db)
            args.update(params)
            return await list_party_library(**args)

    async def test_rebuild_keeps_old_customer_number_for_non_client_records_and_never_for_clients(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(module="customer", serial_no="HZKH2610001", title="乙", customer="", status="T", owner="u1",
                               data={"customer_type": "申请人"}),
                BusinessRecord(module="customer", serial_no="DSR2600900", title="丙", customer="", status="潜在", owner="u1",
                               data={"customer_type": "当事人"}),
            ])
            await db.commit()
        await self._rebuild()
        by_name = {r["subject_name"]: r["party_no"] for r in (await self._list())["items"]}
        self.assertEqual(by_name, {"乙": "HZKH2610001", "丙": "DSR2600900"})
        self.assertEqual([r["subject_name"] for r in (await self._list(name="DSR26009"))["items"]], ["丙"])

    async def test_non_litigation_ipr_case_lists_linked_applicants_but_not_clients(self):
        async with self.sessions() as db:
            client = BusinessRecord(module="customer", serial_no="HZKH-C", title="专利客户", customer="", status="正常", owner="u1",
                                    data={"customer_type": "客户", "customer_managers": ["u1"]})
            applicant = BusinessRecord(module="customer", serial_no="SHKH1400088", title="某大学", customer="", status="T", owner="u1",
                                       data={"customer_type": "申请人"})
            another_client = BusinessRecord(module="customer", serial_no="HZKH-D", title="另一客户", customer="", status="正常", owner="u1",
                                            data={"customer_type": "客户"})
            self_applicant = BusinessRecord(module="customer", serial_no="SHKH1400099", title="自己申请的公司", customer="", status="T", owner="u1",
                                            data={"customer_type": "申请人"})
            db.add_all([client, applicant, another_client, self_applicant])
            await db.flush()
            ipr = BusinessRecord(module="ipr_case", serial_no="CODEX-PU-1", title="专利", customer="专利客户", status="年费监控", owner="u1",
                                 data={"case_type": "国内发明专利", "customer_id": client.id})
            db.add(ipr)
            await db.flush()
            own = BusinessRecord(module="ipr_case", serial_no="CODEX-TM-1", title="商标", customer="自己申请的公司", status="已受理", owner="u1",
                                 data={"case_type": "国内商标", "customer_id": self_applicant.id})
            db.add(own)
            await db.flush()
            db.add(IprCaseCustomer(case_record_id=own.id, customer_record_id=self_applicant.id, is_primary=True, created_by="t"))
            db.add_all([
                IprCaseCustomer(case_record_id=ipr.id, customer_record_id=client.id, is_primary=True, created_by="t"),
                IprCaseCustomer(case_record_id=ipr.id, customer_record_id=applicant.id, is_primary=False, created_by="t"),
                IprCaseCustomer(case_record_id=ipr.id, customer_record_id=another_client.id, is_primary=False, created_by="t"),
            ])
            await db.commit()
        await self._rebuild()
        result = await self._list(case_category="非诉讼")
        rows = {r["case_no"]: r for r in result["items"]}
        self.assertEqual(set(rows), {"CODEX-PU-1", "CODEX-TM-1"})  # 客户类型的关联不进库
        self.assertEqual((rows["CODEX-PU-1"]["subject_name"], rows["CODEX-PU-1"]["party_no"], rows["CODEX-PU-1"]["subject_position"],
                          rows["CODEX-PU-1"]["our_parties"], rows["CODEX-PU-1"]["case_category"]),
                         ("某大学", "SHKH1400088", "申请人", ["专利客户"], "非诉讼"))
        # 申请人就是案件委托人本人时，仍是非诉讼案件产生的当事人
        self.assertEqual((rows["CODEX-TM-1"]["subject_name"], rows["CODEX-TM-1"]["party_no"]), ("自己申请的公司", "SHKH1400099"))
        self.assertEqual(rows["CODEX-PU-1"]["managers"], ["u1"])
        self.assertEqual((await self._list(case_category="其他"))["total"], 2)  # 诉讼案件的数据不受影响

    async def test_rebuild_registers_unlisted_people_in_the_party_table_only(self):
        from datetime import datetime
        yy = f"{datetime.now():%y}"
        async with self.sessions() as db:
            customers_before = len((await db.execute(BusinessRecord.__table__.select().where(BusinessRecord.module == "customer"))).all())
            parties = (await db.execute(PartyRecord.__table__.select().order_by(PartyRecord.id))).all()
        # asyncSetUp 已重建过一次：乙、丙（民事案件）和已删除案件里的丁各登记一个 DSR 当事人
        self.assertEqual([(p.party_no, p.name, p.party_type, p.source_customer_id, p.created_by) for p in parties],
                         [(f"DSR{yy}00001", "乙", "当事人", None, "system"), (f"DSR{yy}00002", "丙", "当事人", None, "system"),
                          (f"DSR{yy}00003", "丁", "当事人", None, "system")])
        self.assertEqual({r["subject_name"]: r["party_no"] for r in (await self._list())["items"]},
                         {"乙": f"DSR{yy}00001", "丙": f"DSR{yy}00002"})
        await self._rebuild()  # 再生成一次不重复登记、编号不变
        async with self.sessions() as db:
            self.assertEqual(len((await db.execute(PartyRecord.__table__.select())).all()), 3)
            self.assertEqual(len((await db.execute(BusinessRecord.__table__.select().where(BusinessRecord.module == "customer"))).all()), customers_before)
        self.assertEqual({r["subject_name"]: r["party_no"] for r in (await self._list())["items"]},
                         {"乙": f"DSR{yy}00001", "丙": f"DSR{yy}00002"})

    async def test_next_serial_counts_only_the_party_table(self):
        from datetime import datetime
        yy = f"{datetime.now():%y}"
        async with self.sessions() as db:
            db.add(BusinessRecord(module="customer", serial_no=f"DSR{yy}00500", title="z", customer="", status="潜在", owner="u1", data={}))
            await db.commit()
            self.assertEqual(await _next_party_serial_no(db), f"DSR{yy}00004")  # 客户表里的 DSR 开头记录不算

    async def test_customer_records_of_party_types_are_copied_with_their_old_numbers(self):
        async with self.sessions() as db:
            db.add(BusinessRecord(module="customer", serial_no="HZKH2610077", title="庚", customer="", status="T", owner="u1",
                                  data={"customer_type": "申请人", "customer_managers": ["u1"]}))
            await db.commit()
        await self._rebuild()
        async with self.sessions() as db:
            copied = (await db.execute(PartyRecord.__table__.select().where(PartyRecord.name == "庚"))).first()
        self.assertEqual((copied.party_no, copied.party_type, copied.created_by), ("HZKH2610077", "申请人", "migration"))
        self.assertIsNotNone(copied.source_customer_id)

    async def test_company_scope_lists_parties_only_and_hides_deleted_cases(self):
        result = await self._list()
        self.assertEqual(result["total"], 2)
        self.assertEqual({r["subject_name"] for r in result["items"]}, {"乙", "丙"})
        self.assertNotIn("甲", {r["subject_name"] for r in result["items"]})  # 客户不显示
        row = result["items"][0]
        self.assertEqual((row["our_parties"], row["our_position"], row["opponent_parties"], row["opponent_position"]),
                         (["甲"], "原告", ["乙", "丙"], "被告"))
        self.assertEqual(row["managers"], ["u1"])

    async def test_people_count_is_people_not_rows(self):
        async with self.sessions() as db:
            db.add(BusinessRecord(module="case", serial_no="CODEX-PL-A3", title="二", customer="甲", status="文书准备", owner="admin",
                                  data={"plaintiff": "甲", "defendant": "乙"}))
            await db.commit()
        await self._rebuild()
        result = await self._list()
        self.assertEqual(result["total"], 3)  # 乙出现在两个案件里
        self.assertEqual(result["people_count"], 2)  # 乙、丙

    async def test_categories_are_separate_with_same_row_shape(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(module="case", serial_no="CODEX-PL-XZ", title="行", customer="甲", status="文书准备", owner="admin",
                               data={"case_type": "行政案件及国家赔偿", "plaintiff": "甲", "defendant": "行政机关"}),
                BusinessRecord(module="case", serial_no="CODEX-PL-MS", title="民", customer="甲", status="文书准备", owner="admin",
                               data={"case_type": "民事争议", "plaintiff": "甲", "defendant": "对方"}),
            ])
            await db.commit()
        await self._rebuild()
        civil, admin_case = await self._list(case_category="民事"), await self._list(case_category="行政")
        self.assertEqual({r["case_no"] for r in civil["items"]}, {"CODEX-PL-MS"})
        self.assertEqual({r["case_no"] for r in admin_case["items"]}, {"CODEX-PL-XZ"})
        self.assertEqual(set(civil["items"][0]), set(admin_case["items"][0]))  # 民事、行政字段一致

    async def test_scopes_mine_department_and_recycle(self):
        mine = {"username": "u1", "role": "user", "_page_menu_capability": True}
        self.assertEqual((await self._list(scope="mine", identity=mine))["total"], 2)  # 甲的客户管理人是 u1
        self.assertEqual((await self._list(scope="department", identity=mine))["total"], 2)
        other_dept = {"username": "u3", "role": "user", "_page_menu_capability": True}
        self.assertEqual((await self._list(scope="mine", identity=other_dept))["total"], 0)
        self.assertEqual((await self._list(scope="department", identity=other_dept))["total"], 0)
        # 已删除案件只在回收站范围出现，且按管理人划分
        self.assertEqual({r["subject_name"] for r in (await self._list(scope="recycle", identity=mine))["items"]}, {"丁"})
        self.assertEqual((await self._list(scope="recycle", identity=other_dept))["total"], 0)
        self.assertEqual({r["case_no"] for r in (await self._list(scope="recycle"))["items"]}, {"CODEX-PL-A2"})

    async def test_filters_and_rebuild_is_repeatable(self):
        self.assertEqual([r["subject_name"] for r in (await self._list(name="乙"))["items"]], ["乙"])
        self.assertEqual((await self._list(case_no="NOPE"))["total"], 0)
        await self._rebuild()
        self.assertEqual((await self._list())["total"], 2)


if __name__ == "__main__":
    unittest.main()


class CaseLitigantRegistrationTest(unittest.IsolatedAsyncioTestCase):
    """案件里新录入的当事人只写当事人表（DSR 编号），不写客户表。"""

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_new_litigants_become_party_records_and_existing_names_are_skipped(self):
        from datetime import datetime
        from app.core.crm import _persist_case_litigant_customers
        yy = f"{datetime.now():%y}"
        async with self.sessions() as db:
            db.add(User(username="u1", display_name="员工", department="一部", role="user", role_ids=["user"], password_hash="x"))
            db.add(BusinessRecord(module="customer", serial_no="HZKH2610001", title="老当事人", customer="", status="T", owner="u1",
                                  data={"customer_type": "申请人"}))
            case_record = BusinessRecord(module="case", serial_no="CODEX-LT-1", title="案", customer="甲", status="新案待分配", owner="u1", data={})
            db.add(case_record)
            await db.flush()
            customers_before = len((await db.execute(BusinessRecord.__table__.select().where(BusinessRecord.module == "customer"))).all())
            created = await _persist_case_litigant_customers(
                case_record, {"被告": ["新对方", "老当事人"]}, {"username": "u1"}, db,
                party_identities={"新对方": {"organization_type": "个人", "identity_no": "110101199001011234"}})
            await db.commit()
            parties = (await db.execute(PartyRecord.__table__.select())).all()
            customers_after = len((await db.execute(BusinessRecord.__table__.select().where(BusinessRecord.module == "customer"))).all())
        self.assertEqual([c.party_no for c in created], [f"DSR{yy}00001"])
        self.assertEqual([(p.party_no, p.name, p.party_type, p.owner, p.department, p.created_by) for p in parties],
                         [(f"DSR{yy}00001", "新对方", "当事人", "u1", "一部", "u1")])
        self.assertEqual(parties[0].data["identity_no"], "110101199001011234")
        self.assertEqual(customers_after, customers_before)  # 客户表没有新增

        async with self.sessions() as db:
            again = await _persist_case_litigant_customers(case_record, {"被告": ["新对方"]}, {"username": "u1"}, db)
        self.assertEqual(again, [])  # 当事人表里已有的不重复登记
