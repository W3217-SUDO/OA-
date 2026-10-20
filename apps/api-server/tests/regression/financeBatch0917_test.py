"""9.17 批次真实接口回归，数据库仅使用内存并在每例销毁。"""
import unittest
from datetime import date
from sqlalchemy import select, func
from finance_0916_batch_test import FinanceBatchTest, API, IDENTITY, app, current_identity
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment, JobRole, SystemParameter, User, WorkflowEvent

class Batch0917Test(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = FinanceBatchTest.asyncTearDown
    async def asyncSetUp(self):
        await FinanceBatchTest.asyncSetUp(self)
        async with self.sessions() as db:
            db.add(SystemParameter(category='fee_type',code='AGENCY-REFUND',name='律师代理费(退费)',extra={'parent_code':'AGENCY'},is_active=True))
            await db.commit()

    async def test_source_migration_and_bank_import(self):
        from app.core.incoming_payment_sources import backfill_incoming_sources
        async with self.sessions() as db:
            rows=[]
            for suffix in ['HK20260917120000123456','HK202609171200001234562','HKICBCabcdef','HK20260917120000123457','202601010001']:
                item=IncomingPayment(receipt_no=suffix,received_date=date(2026,9,17),amount=20,payer_name='回归单位',operator=IDENTITY['username'])
                db.add(item);rows.append(item)
            db.add(BusinessRecord(module='finance',serial_no='CODEX-0917-ipr-arrival',title='系统到账',owner=IDENTITY['username'],data={'arrival_receipt_no':'HK20260917120000123457'}))
            await db.commit();ids=[row.id for row in rows];timestamps=[row.updated_at for row in rows]
        async with self.engine.begin() as connection:
            await connection.run_sync(backfill_incoming_sources)
            await connection.run_sync(backfill_incoming_sources)
        async with self.sessions() as db:
            rows=[await db.get(IncomingPayment,key) for key in ids]
            self.assertEqual([row.source_kind for row in rows],['manual','bank_import','bank_import','system','unknown'])
            self.assertEqual([row.updated_at for row in rows],timestamps)
        content='对方户名,银行流水号,到账日期,到账金额\n回归单位,TEST-BANK-0917,2026-09-17,10\n'.encode('utf-8-sig')
        result=await self.client.post(f'{API}/finance/incoming-payments/import',files={'file':('receipt.csv',content,'text/csv')})
        self.assertEqual(result.status_code,200,result.text)
        async with self.sessions() as db:
            imported=await db.scalar(select(IncomingPayment).where(IncomingPayment.bank_reference=='TEST-BANK-0917'))
            self.assertIsNotNone(imported);self.assertEqual(imported.source_kind,'bank_import')

    async def test_manual_receipt_edit_and_source_restrictions(self):
        body={'received_date':'2026-09-17','amount':100,'payer_name':'回归付款单位','remark':'回款方式：转账'}
        result=await self.client.post(f'{API}/finance/incoming-payments',json=body)
        self.assertEqual(result.status_code,201,result.text)
        receipt=result.json(); self.assertEqual(receipt['source_kind'],'manual')
        path=f"{API}/finance/incoming-payments/{receipt['id']}"
        result=await self.client.put(path,json={**body,'amount':120})
        self.assertEqual(result.status_code,200,result.text)
        async with self.sessions() as db:
            item=await db.get(IncomingPayment,receipt['id']); self.assertEqual(item.amount,120)
            item.allocations=[{'amount':30,'fee_type':'官方费用'}];item.allocated_amount=30;item.status='部分分配';await db.commit()
        result=await self.client.put(path,json={**body,'amount':20})
        self.assertEqual(result.status_code,422,result.text)
        result=await self.client.put(path,json={**body,'amount':30})
        self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['status'],'已分配')
        self.assertEqual(result.json()['allocations'][0]['amount'],30)
        result=await self.client.put(path,json={**body,'customer':'其他客户'})
        self.assertEqual(result.status_code,409,result.text)
        for source in ['bank_import','system','unknown']:
            async with self.sessions() as db:
                item=await db.get(IncomingPayment,receipt['id']);item.source_kind=source;await db.commit()
            result=await self.client.put(path,json=body);self.assertEqual(result.status_code,403,result.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(IncomingPayment,receipt['id'])).amount,30)
        app.dependency_overrides[current_identity]=lambda:{'username':'unrelated','role':'user'}
        result=await self.client.put(path,json=body)
        self.assertEqual(result.status_code,403,result.text)
        app.dependency_overrides[current_identity]=lambda:IDENTITY

    async def test_agency_refund_atomic_duplicate_and_projection(self):
        body={'fee_record_id':self.fee_id,'case_no':'CODEX-0916-case','customer':'Batch customer','court':'法院','original_payment_no':'receipt','amount':40,'applicant':'回归申请人','request_key':'batch0917-refund'}
        result=await self.client.post(f'{API}/finance/refunds',json=body)
        self.assertEqual(result.status_code,201,result.text);refund=result.json()
        result2=await self.client.post(f'{API}/finance/refunds',json=body)
        self.assertEqual(result2.status_code,201,result2.text);self.assertEqual(refund['id'],result2.json()['id'])
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,refund['data']['refund_fee_id'])
            self.assertEqual(fee.data['amount'],40);self.assertEqual(fee.data['source_fee_id'],self.fee_id)
            self.assertEqual(fee.title,'律师代理费(退费)');self.assertEqual(fee.data['expense_scope'],'律所')
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module=='refund')),1)
        result=await self.client.patch(f"{API}/finance/refunds/{refund['id']}/amount",json={'amount':50})
        self.assertEqual(result.status_code,200,result.text)
        async with self.sessions() as db:self.assertEqual((await db.get(BusinessRecord,refund['data']['refund_fee_id'])).data['amount'],50)
        result=await self.client.post(f'{API}/finance/refunds',json={**body,'request_key':'second','amount':51})
        self.assertEqual(result.status_code,422,result.text)
        result=await self.client.get(f'{API}/cases/{self.case_id}/relations')
        self.assertEqual(result.status_code,200,result.text)
        fees=result.json().get('fees',[])
        original=next(row for row in fees if row['id']==self.fee_id)
        self.assertEqual(original['data']['refund_requested_amount'],50)
        self.assertEqual(original['data']['refunded_amount'],0)
        async with self.sessions() as db:
            ft=await db.scalar(select(SystemParameter).where(SystemParameter.code=='AGENCY-REFUND'));ft.is_active=False;await db.commit()
            before=await db.scalar(select(func.count()).select_from(BusinessRecord))
        result=await self.client.post(f'{API}/finance/refunds',json={**body,'request_key':'missing-type','amount':10})
        self.assertEqual(result.status_code,422,result.text)
        async with self.sessions() as db:self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord)),before)

    async def test_zero_court_refund_keeps_historical_agency_fee_and_projects_zero(self):
        """法院退费归零只清零案件退费投影，不新增或改写历史律师代理费退费。"""
        body = {
            'fee_record_id': self.fee_id,
            'case_no': 'CODEX-0916-case',
            'customer': 'Batch customer',
            'court': '法院',
            'original_payment_no': 'receipt-zero',
            'amount': 40,
            'applicant': '回归申请人',
            'request_key': 'batch0917-zero-refund',
        }
        result = await self.client.post(f'{API}/finance/refunds', json=body)
        self.assertEqual(result.status_code, 201, result.text)
        refund = result.json()
        agency_fee_id = refund['data']['refund_fee_id']
        async with self.sessions() as db:
            agency_fee = await db.get(BusinessRecord, agency_fee_id)
            self.assertEqual(agency_fee.data['amount'], 40)
            before_agency_count = await db.scalar(select(func.count()).select_from(BusinessRecord).where(
                BusinessRecord.module == 'finance',
                BusinessRecord.data['refund_record_id'].as_integer() == refund['id'],
            ))
            self.assertEqual(before_agency_count, 1)

        preview = await self.client.get(
            f'{API}/cases/{self.case_id}/commission-preview', params={'source_fee_id': agency_fee_id},
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        commission = await self.client.post(f'{API}/cases/{self.case_id}/commissions', json={
            'source_fee_id': agency_fee_id,
            'items': [{'preview_key': preview.json()['items'][0]['preview_key'], 'actual_amount': 4}],
        })
        self.assertEqual(commission.status_code, 201, commission.text)
        commission_id = commission.json()['items'][0]['id']
        self.assertEqual(commission.json()['items'][0]['status'], '待审批')
        self.assertTrue(commission.json()['items'][0]['data']['is_refund'])
        for kind, expected in (('refund', True), ('commission', False)):
            queue = await self.client.get(f'{API}/finance/internal-review-requests', params={'kind': kind})
            self.assertEqual(queue.status_code, 200, queue.text)
            self.assertEqual(commission_id in {row['id'] for row in queue.json()['items']}, expected)
        payments = await self.client.get(f'{API}/finance/payment-applications/query', params={'scope': 'mine'})
        self.assertEqual(payments.status_code, 200, payments.text)
        self.assertNotIn(commission_id, {row['id'] for row in payments.json()['items']})
        async with self.sessions() as db:
            preserved = {}
            for record_id in (agency_fee_id, commission_id):
                item = await db.get(BusinessRecord, record_id)
                preserved[record_id] = (item.status, dict(item.data), item.updated_at)
            before_refunds = await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == 'refund'))
            before_transactions = await db.scalar(select(func.count()).select_from(FinanceTransaction))

        # 零值动作只修改源费投影，反复打开保存也不创建普通退款业务单。
        zero_body = {**body, 'amount': 0, 'request_key': 'batch0917-create-zero'}
        zero_path = f'{API}/finance/fees/{self.fee_id}/court-refund/clear-projection'
        zero = await self.client.post(zero_path)
        self.assertEqual(zero.status_code, 200, zero.text)
        self.assertEqual(zero.json()['id'], self.fee_id)
        self.assertEqual(zero.json()['module'], 'finance')
        self.assertNotIn('refund_fee_id', zero.json()['data'])
        retry = await self.client.post(zero_path)
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(retry.json()['id'], zero.json()['id'])
        invalid = await self.client.post(f'{API}/finance/refunds', json=zero_body)
        self.assertEqual(invalid.status_code, 422, invalid.text)
        not_a_refund = await self.client.post(f'{API}/finance/refunds/{self.fee_id}/submit', json={})
        self.assertEqual(not_a_refund.status_code, 404, not_a_refund.text)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == 'refund')), before_refunds)
            self.assertEqual(await db.scalar(select(func.count()).select_from(FinanceTransaction)), before_transactions)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(
                WorkflowEvent.record_id == self.fee_id, WorkflowEvent.action == '法院退费显示归零',
            )), 1)
            for record_id, snapshot in preserved.items():
                item = await db.get(BusinessRecord, record_id)
                self.assertEqual((item.status, item.data, item.updated_at), snapshot)
            self.assertEqual((await db.get(BusinessRecord, self.fee_id)).data['refund_amount_override'], 0)
        relations = await self.client.get(f'{API}/cases/{self.case_id}/relations')
        self.assertEqual(relations.status_code, 200, relations.text)
        original = next(row for row in relations.json()['fees'] if row['id'] == self.fee_id)
        self.assertEqual(original['data']['refund_amount'], 0)

        positive = await self.client.post(f'{API}/finance/refunds', json={
            **body, 'amount': 10, 'request_key': 'batch0917-positive-after-zero',
        })
        self.assertEqual(positive.status_code, 201, positive.text)
        relations = await self.client.get(f'{API}/cases/{self.case_id}/relations')
        self.assertEqual(relations.status_code, 200, relations.text)
        original = next(row for row in relations.json()['fees'] if row['id'] == self.fee_id)
        self.assertEqual(original['data']['refund_amount'], 50)

        result = await self.client.patch(
            f"{API}/finance/refunds/{refund['id']}/amount",
            json={'amount': 0, 'comment': '归零回归'},
        )
        self.assertEqual(result.status_code, 200, result.text)
        async with self.sessions() as db:
            agency_fee = await db.get(BusinessRecord, agency_fee_id)
            self.assertEqual(agency_fee.data['amount'], 40)
            after_agency_count = await db.scalar(select(func.count()).select_from(BusinessRecord).where(
                BusinessRecord.module == 'finance',
                BusinessRecord.data['refund_record_id'].as_integer() == refund['id'],
            ))
            self.assertEqual(after_agency_count, before_agency_count)
            source_fee = await db.get(BusinessRecord, self.fee_id)
            self.assertEqual(source_fee.data['refund_amount_override'], 0)

        relations = await self.client.get(f'{API}/cases/{self.case_id}/relations')
        self.assertEqual(relations.status_code, 200, relations.text)
        original = next(row for row in relations.json().get('fees', []) if row['id'] == self.fee_id)
        self.assertEqual(original['data']['refund_amount'], 0)
        self.assertEqual(original['data']['refund_requested_amount'], 0)

        restored = await self.client.patch(
            f"{API}/finance/refunds/{refund['id']}/amount", json={'amount': 40},
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        async with self.sessions() as db:
            self.assertNotIn('refund_amount_override', (await db.get(BusinessRecord, self.fee_id)).data)

    async def test_refund_request_key_requires_equal_payload_and_lookup_is_owner_scoped(self):
        body = {
            'fee_record_id': self.fee_id, 'case_no': 'CODEX-0916-case', 'customer': 'Batch customer',
            'court': '法院', 'original_payment_no': 'receipt-key', 'amount': 40,
            'applicant': '回归申请人', 'request_key': 'batch0917-payload-key',
        }
        first = await self.client.post(f'{API}/finance/refunds', json=body)
        self.assertEqual(first.status_code, 201, first.text)
        retry = await self.client.post(f'{API}/finance/refunds', json=body)
        self.assertEqual(retry.status_code, 201, retry.text)
        self.assertEqual(retry.json()['id'], first.json()['id'])
        for changed in ({'amount': 20}, {'court': '其他法院'}, {'remark': '另一项申请'}, {'refund_account': 'different'}):
            conflict = await self.client.post(f'{API}/finance/refunds', json={**body, **changed})
            self.assertEqual(conflict.status_code, 409, conflict.text)
        lookup = f'{API}/finance/fees/{self.fee_id}/court-refund/request'
        found = await self.client.get(lookup, params={'request_key': body['request_key']})
        self.assertEqual(found.status_code, 200, found.text)
        self.assertEqual(found.json()['id'], first.json()['id'])
        missing = await self.client.get(lookup, params={'request_key': 'not-committed-or-still-running'})
        self.assertEqual(missing.status_code, 404, missing.text)
        async with self.sessions() as db:
            db.add(User(username='CODEX-B-other-admin', display_name='隔离其他管理员', role='admin',
                        department='test', password_hash='unused', is_active=True))
            await db.commit()
        app.dependency_overrides[current_identity] = lambda: {'username': 'CODEX-B-other-admin', 'role': 'admin', 'department': 'test'}
        try:
            denied = await self.client.get(lookup, params={'request_key': body['request_key']})
            self.assertEqual(denied.status_code, 404, denied.text)
        finally:
            app.dependency_overrides[current_identity] = lambda: IDENTITY
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == 'refund')), 1)
            saved = await db.get(BusinessRecord, first.json()['id'])
            self.assertEqual(saved.data['amount'], 40)
        # 原始金额快照也参与比较，不把按分进位后的相同金额视为相同请求。
        fractional = {**body, 'request_key': 'batch0917-fractional-key', 'amount': .015}
        created = await self.client.post(f'{API}/finance/refunds', json=fractional)
        self.assertEqual(created.status_code, 201, created.text)
        repeated = await self.client.post(f'{API}/finance/refunds', json=fractional)
        self.assertEqual(repeated.status_code, 201, repeated.text)
        self.assertEqual(repeated.json()['id'], created.json()['id'])
        self.assertEqual(created.json()['data']['amount'], .02)
        changed = await self.client.post(f'{API}/finance/refunds', json={**fractional, 'amount': .02})
        self.assertEqual(changed.status_code, 409, changed.text)
        # 核对旧版已存在的零元申请：同键改正数必须冲突，不能冒称正数成功。
        async with self.sessions() as db:
            old = await db.get(BusinessRecord, first.json()['id'])
            old_data = dict(old.data)
            old_data.pop('request_payload')
            old.data = {**old_data, 'amount': 0}
            await db.commit()
        old_zero = await self.client.get(lookup, params={'request_key': body['request_key']})
        self.assertEqual(old_zero.status_code, 200, old_zero.text)
        self.assertEqual(old_zero.json()['data']['amount'], 0)
        old_conflict = await self.client.post(f'{API}/finance/refunds', json=body)
        self.assertEqual(old_conflict.status_code, 409, old_conflict.text)

    async def test_refund_create_canonical_amount_and_update_keeps_zero_contract(self):
        from fastapi import HTTPException
        from app.agent_mcp.catalog import ToolCatalog
        from app.api_schemas.finance import LitigationRefundInput, RefundAmountUpdateInput
        from app.core.finance import _round_fee_amount

        body = {
            'fee_record_id': self.fee_id, 'case_no': 'CODEX-0916-case', 'customer': 'Batch customer',
            'court': '法院', 'original_payment_no': 'receipt-cent', 'amount': .01,
            'applicant': '回归申请人', 'request_key': 'batch0917-cent-key',
        }
        zero_path = f'{API}/finance/fees/{self.fee_id}/court-refund/clear-projection'
        zero = await self.client.post(zero_path)
        self.assertEqual(zero.status_code, 200, zero.text)
        async with self.sessions() as db:
            source_before = dict((await db.get(BusinessRecord, self.fee_id)).data)
            counts_before = [await db.scalar(select(func.count()).select_from(model))
                             for model in (BusinessRecord, WorkflowEvent, FinanceTransaction)]
        catalog = ToolCatalog(app)
        create_tool = next(spec for spec in catalog.tools if spec.path == f'{API}/finance/refunds' and spec.method == 'POST')
        update_tool = next(spec for spec in catalog.tools if spec.path == f'{API}/finance/refunds/{{refund_id}}/amount')
        self.assertEqual(create_tool.input_schema['properties']['body']['properties']['amount']['exclusiveMinimum'], 0)
        self.assertEqual(update_tool.input_schema['properties']['body']['properties']['amount']['minimum'], 0)
        self.assertEqual(RefundAmountUpdateInput(amount=0).amount, 0)
        self.assertEqual(_round_fee_amount(0), 0)
        invalid = await self.client.post(f'{API}/finance/refunds', json={**body, 'amount': 0})
        self.assertEqual(invalid.status_code, 422, invalid.text)
        with self.assertRaises(HTTPException) as invalid_mcp:
            create_tool.validate_arguments({'body': {**body, 'amount': 0}})
        self.assertEqual(invalid_mcp.exception.status_code, 422)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, self.fee_id)).data, source_before)
            self.assertEqual([await db.scalar(select(func.count()).select_from(model))
                              for model in (BusinessRecord, WorkflowEvent, FinanceTransaction)], counts_before)
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == 'refund')), 0)
        # 保留485的ROUND_UP：合法正数按原规则量化，幂等仍比较原始请求而非量化结果。
        for index, value in enumerate((.001, .004, .005, .01)):
            with self.subTest(amount=value):
                request = {**body, 'amount': value, 'request_key': f"{body['request_key']}-{index}"}
                self.assertEqual(_round_fee_amount(value), .01)
                self.assertEqual(LitigationRefundInput(**request).amount, value)
                self.assertEqual(create_tool.validate_arguments({'body': request})['body']['amount'], value)
                valid = await self.client.post(f'{API}/finance/refunds', json=request)
                self.assertEqual(valid.status_code, 201, valid.text)
                refund = valid.json()
                self.assertEqual(refund['data']['amount'], .01)
                self.assertEqual(refund['data']['request_payload']['amount'], value)
                repeated = await self.client.post(f'{API}/finance/refunds', json=request)
                self.assertEqual(repeated.status_code, 201, repeated.text)
                self.assertEqual(repeated.json()['id'], refund['id'])
                conflict = await self.client.post(f'{API}/finance/refunds', json={
                    **request, 'amount': .01 if value < .01 else .02,
                })
                self.assertEqual(conflict.status_code, 409, conflict.text)
                async with self.sessions() as db:
                    self.assertEqual((await db.get(BusinessRecord, refund['data']['refund_fee_id'])).data['amount'], .01)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == 'refund')), 4)
        # update不收紧ge=0；只让退款单与派生费使用同一既有量化金额。
        update_path = f"{API}/finance/refunds/{refund['id']}/amount"
        for value in (.001, .004, .005):
            changed = await self.client.patch(update_path, json={'amount': value})
            self.assertEqual(changed.status_code, 200, changed.text)
            self.assertEqual(changed.json()['data']['amount'], .01)
            async with self.sessions() as db:
                self.assertEqual((await db.get(BusinessRecord, refund['data']['refund_fee_id'])).data['amount'], .01)
        cleared = await self.client.patch(update_path, json={'amount': 0})
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertEqual(cleared.json()['data']['amount'], 0)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, self.fee_id)).data['refund_amount_override'], 0)
            self.assertEqual((await db.get(BusinessRecord, refund['data']['refund_fee_id'])).data['amount'], .01)
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == 'refund')), 4)

    async def test_zero_projection_requires_action_and_cannot_use_generic_update(self):
        viewer = {'username': 'CODEX-B-refund-viewer', 'role': 'user', 'department': 'test'}
        async with self.sessions() as db:
            db.add_all([
                JobRole(code='CODEX-B-VIEWER', name='隔离费用查看岗', permissions=['case-mine', 'finance-fee-query'],
                        data_scope='全所数据', is_active=True),
                User(username=viewer['username'], display_name='隔离费用查看人', role='user', department='test',
                     password_hash='unused', is_active=True, profile={'permission_role_code': 'CODEX-B-VIEWER'}),
            ])
            await db.commit()
            before = dict((await db.get(BusinessRecord, self.fee_id)).data)
        app.dependency_overrides[current_identity] = lambda: viewer
        try:
            visible = await self.client.get(f'{API}/records/{self.fee_id}')
            self.assertEqual(visible.status_code, 200, visible.text)
            denied = await self.client.post(f'{API}/finance/fees/{self.fee_id}/court-refund/clear-projection')
            self.assertEqual(denied.status_code, 403, denied.text)
            self.assertIn('案件费用操作权限', denied.text)
        finally:
            app.dependency_overrides[current_identity] = lambda: IDENTITY
        bypass = await self.client.patch(f'{API}/records/{self.fee_id}', json={
            'data': {**before, 'refund_amount_override': 0, 'refund_requested_amount_override': 0},
        })
        self.assertEqual(bypass.status_code, 200, bypass.text)
        self.assertFalse(bypass.json()['IsSuccess'])
        self.assertIn('专用入口', bypass.json()['Message'])
        create_bypass = await self.client.post(f'{API}/records', json={
            'module': 'finance', 'serial_no': 'CODEX-B-generic-bypass', 'title': '隔离绕过尝试',
            'data': {**before, 'refund_amount_override': 0, 'refund_requested_amount_override': 0},
        })
        self.assertEqual(create_bypass.status_code, 422, create_bypass.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, self.fee_id)).data, before)
            self.assertIsNone(await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == 'CODEX-B-generic-bypass')))
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), 0)

    async def test_zero_projection_mcp_requires_human_confirmation_and_lookup_is_realtime(self):
        from unittest.mock import AsyncMock, patch
        from fastapi import HTTPException
        from app.agent_mcp import service
        from app.agent_mcp.auth import AuthContext, _auth_context
        from app.agent_mcp.catalog import ToolCatalog

        catalog = ToolCatalog(app)
        endpoint = f'{API}/finance/fees/{{fee_id}}/court-refund/clear-projection'
        tool = next(spec for spec in catalog.tools if spec.path == endpoint and spec.method == 'POST')
        self.assertTrue(tool.is_write)
        lookup_path = f'{API}/finance/fees/{{fee_id}}/court-refund/request'
        route = next(route for route in app.routes if getattr(route, 'path', '') == lookup_path)
        self.assertIs(route.dependant.call, route.endpoint)
        token = _auth_context.set(AuthContext(app, 'CODEX-B-isolated-token', {
            'type': 'http', 'path': f'{API}/mcp', 'method': 'POST', 'headers': [],
        }))
        try:
            with patch.object(service, 'SessionLocal', self.sessions), \
                 patch.object(service, 'authenticated_identity', new=AsyncMock(return_value=IDENTITY)), \
                 patch.object(service, 'execute_original', new=AsyncMock()) as execute:
                pending = await service.call_tool(tool.name, {'path': {'fee_id': self.fee_id}})
                self.assertEqual(pending['status'], 'pending')
                self.assertTrue(pending['preview']['requires_confirmation'])
                execute.assert_not_awaited()
                with self.assertRaises(HTTPException) as denied:
                    async with self.sessions() as db:
                        await service.decide_tool_request(pending['request_id'], 'approved', IDENTITY, db)
                self.assertEqual(denied.exception.status_code, 403)
                frontend_path = f"{API}/agent-tools/requests/{pending['request_id']}/decision"
                frontend_token = _auth_context.set(AuthContext(app, 'CODEX-B-isolated-token', {
                    'type': 'http', 'path': frontend_path, 'method': 'POST', 'headers': [],
                }))
                try:
                    with self.assertRaises(HTTPException) as untrusted:
                        async with self.sessions() as db:
                            await service.decide_tool_request(pending['request_id'], 'approved', IDENTITY, db)
                    self.assertEqual(untrusted.exception.status_code, 403)
                    execute.assert_not_awaited()
                finally:
                    _auth_context.reset(frontend_token)
            async with self.sessions() as db:
                self.assertNotIn('refund_amount_override', (await db.get(BusinessRecord, self.fee_id)).data)
                self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == 'refund')), 0)
                confirmation = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == 'agent_mcp_action'))
                self.assertEqual(confirmation.status, '待确认')
        finally:
            _auth_context.reset(token)

    async def test_official_refund_atomic_duplicate_and_projection(self):
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, 'fee_type': '官方费用', 'expense_subtype': '官费', 'expense_scope': '律所'}
            await db.commit()
        await self.test_agency_refund_atomic_duplicate_and_projection()
        async with self.sessions() as db:
            original = await db.get(BusinessRecord, self.fee_id)
            self.assertEqual(original.data['fee_type'], '官方费用')
            self.assertEqual(original.data['expense_subtype'], '官费')

    async def test_all_firm_fee_types_commission_preview_and_save(self):
        # 真实返工场景：未单独录入开庭律师，页面和计算均采用首位经办律师。
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {key: value for key, value in case.data.items() if key != 'hearing_lawyer_usernames'}
            await db.commit()
        for kind in ['官方费用','其他费用','代理费']:
            async with self.sessions() as db:
                fee=await db.get(BusinessRecord,self.fee_id);fee.data={**fee.data,'fee_type':kind,'expense_scope':'律所'};await db.commit()
            result=await self.client.get(f'{API}/cases/{self.case_id}/commission-preview',params={'source_fee_id':self.fee_id})
            self.assertEqual(result.status_code,200,result.text);preview=result.json()
            self.assertEqual(preview['source_fee']['fee_type'],kind)
            result=await self.client.post(f'{API}/cases/{self.case_id}/commissions',json={'source_fee_id':self.fee_id,'items':[{'preview_key':preview['items'][0]['preview_key'],'actual_amount':10}]})
            self.assertEqual(result.status_code,201,result.text)
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,self.fee_id);fee.data={**fee.data,'expense_scope':'平台'};await db.commit()
        result=await self.client.get(f'{API}/cases/{self.case_id}/commission-preview',params={'source_fee_id':self.fee_id})
        self.assertEqual(result.status_code,422,result.text)

    async def test_explicit_invalid_hearing_and_inactive_account_still_block(self):
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            original = dict(case.data)
            case.data = {**original, 'hearing_lawyer_usernames': ['missing-account']}
            await db.commit()
        result = await self.client.get(f'{API}/cases/{self.case_id}/commission-preview', params={'source_fee_id': self.fee_id})
        self.assertEqual(result.status_code, 422, result.text)
        self.assertIn('开庭律师', result.text)
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {key: value for key, value in original.items() if key != 'hearing_lawyer_usernames'}
            user = await db.scalar(select(User).where(User.username == IDENTITY['username']))
            user.is_active = False
            await db.commit()
        result = await self.client.get(f'{API}/cases/{self.case_id}/commission-preview', params={'source_fee_id': self.fee_id})
        self.assertEqual(result.status_code, 422, result.text)
        self.assertIn('开庭律师', result.text)

    async def test_case_list_real_task_priority_and_permission(self):
        async with self.sessions() as db:
            case=await db.get(BusinessRecord,self.case_id);case.data={**case.data,'task_name':'过时快照','task_content':'不能显示'}
            items=[]
            for number,status,deadline,links in [(1,'处理中','2026-01-01',{'case_id':self.case_id}),(2,'待接收','2026-10-20',{'case_no':'CODEX-0916-case'}),(3,'待接收','2026-10-10',{'case_ids':[self.case_id]}),(4,'已完成','2026-01-01',{'case_ids':[self.case_id]})]:
                task=BusinessRecord(module='task',serial_no=f'CODEX-0917-task-{number}',title=f'真实任务{number}',owner=IDENTITY['username'],status=status,data={**links,'deadline':deadline,'content':f'任务正文{number}','initiator':IDENTITY['username']})
                db.add(task);items.append(task)
            await db.commit();taskid=items[2].id
        result=await self.client.post(f'{API}/cases/search',json={})
        self.assertEqual(result.status_code,200,result.text);case=next(row for row in result.json()['items'] if row['id']==self.case_id)
        self.assertEqual(case['data']['task_id'],taskid);self.assertEqual(case['data']['task_content'],'任务正文3')
        target=await self.client.get(f'{API}/tasks',params={'serial_no':case['data']['task_serial_no'],'scope':'company','page_size':20})
        self.assertEqual(target.status_code,200,target.text)
        self.assertIn(taskid,[row['id'] for row in target.json()['items']])
        async with self.sessions() as db:
            from app.core.case_list_tasks import attach_case_list_tasks
            rows=[{'id':self.case_id,'serial_no':'CODEX-0916-case','data':{'task_name':'不能泄露'}}]
            await attach_case_list_tasks(rows,{'username':'unrelated','role':'staff'},db)
            self.assertNotIn('task_name',rows[0]['data'])
        async with self.sessions() as db:
            task=await db.get(BusinessRecord,taskid);task.status='已完成';await db.commit()
        result=await self.client.post(f'{API}/cases/search',json={})
        case=next(row for row in result.json()['items'] if row['id']==self.case_id)
        self.assertEqual(case['data']['task_name'],'真实任务2')

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Batch0917Test))
    raise SystemExit(not result.wasSuccessful())
