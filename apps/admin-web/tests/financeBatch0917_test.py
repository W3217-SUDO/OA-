"""9.17 批次真实接口回归，数据库仅使用内存并在每例销毁。"""
import unittest
from datetime import date
from sqlalchemy import select, func
from finance_0916_batch_test import FinanceBatchTest, API, IDENTITY, app, current_identity
from app.models import BusinessRecord, IncomingPayment, SystemParameter, User

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

    async def test_all_firm_fee_types_commission_preview_and_save(self):
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
