"""9.15 batch API regressions on an isolated in-memory database."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from app.database import Base, get_db
from app.security import current_identity
from app.models import BusinessRecord, User, IncomingPayment, FileAttachment
from app.areas.finance.router import router
from app.core.finance_batch_parity import group_commission_applications
from app.config import settings
from sqlalchemy import select

API = settings.api_prefix
IDENTITY = {'username': 'CODEX-0915-admin', 'role': 'admin', 'department': 'Test', 'display_name': 'Test'}


class BatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:', poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.temp = tempfile.TemporaryDirectory()
        self.upload_patch = patch('app.areas.finance.payment_workflow.UPLOAD_ROOT', Path(self.temp.name))
        self.upload_patch.start()
        self.app = FastAPI()
        self.app.include_router(router)
        async def database():
            async with self.sessions() as db:
                yield db
        self.app.dependency_overrides[get_db] = database
        self.app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test')
        async with self.sessions() as db:
            db.add(User(username=IDENTITY['username'], display_name='Test', role='admin', department='Test', password_hash='x', is_active=True))
            customer = self.record('customer', 'customer', {})
            contract = self.record('contract', 'contract', {})
            db.add_all([customer, contract]); await db.flush()
            case = self.record('case', 'case', {'contract_id':contract.id,'contract_no':contract.serial_no})
            db.add(case); await db.flush()
            data = {'amount':100,'fee_type':'官方费用','expense_scope':'律所','expense_subtype':'一审诉讼费',
                    'case_no':case.serial_no,'case_id':case.id,'contract_id':contract.id,'contract_no':contract.serial_no,
                    'refund_amount':50,'payment_status':'待付款','payee':'测试法院'}
            fee = self.record('finance','fee',data,'已审批')
            internal = self.record('finance','internal',{**data,'fee_type':'内部费用','expense_scope':'内部'})
            payment = IncomingPayment(receipt_no='CODEX-0915-receipt',received_date=date.today(), amount=50,
                payer_name='测试法院',status='待分配',claimed_customer=customer.title,claimant=IDENTITY['username'],operator=IDENTITY['username'])
            db.add_all([fee,internal,payment]); await db.commit()
            self.fee_id,self.internal_id,self.receipt_id=fee.id,internal.id,payment.id

    def record(self,module,name,data,status='正常'):
        return BusinessRecord(module=module,serial_no='CODEX-0915-'+name,title='CODEX-0915-'+name,
            customer='CODEX-0915-customer',status=status,owner=IDENTITY['username'],department='Test',data=data)

    async def asyncTearDown(self):
        await self.client.aclose(); await self.engine.dispose()
        self.upload_patch.stop(); self.temp.cleanup()

    async def test_payment_submit_writeoff_and_voucher_persistence(self):
        path=f'{API}/finance/payment-workflow/{self.fee_id}'
        response=await self.client.post(path+'/submit')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'待核销')
        self.assertEqual((await self.client.post(path+'/submit')).status_code,409)
        values={'paid_date':str(date.today()),'amount':'100','payment_method':'银行卡','invoice_no':'TEST-VOUCHER'}
        self.assertEqual((await self.client.post(path+'/writeoff',data=values)).status_code,422)
        response=await self.client.post(path+'/writeoff',data=values,files=[('files',('proof.txt',b'CODEX-0915-proof','text/plain'))])
        self.assertEqual(response.status_code,200,response.text)
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,self.fee_id)
            self.assertEqual(fee.status,'已付款')
            invoice_id=fee.data['invoice_record_id']
            attachment=await db.scalar(select(FileAttachment).where(FileAttachment.record_id==invoice_id))
            self.assertEqual(Path(attachment.path).read_bytes(),b'CODEX-0915-proof')
        response=await self.client.post(path+'/writeoff',data=values,files=[('files',('proof.txt',b'proof'))])
        self.assertEqual(response.status_code,409)

    async def test_refund_partial_full_and_revoke(self):
        path=f'{API}/finance/incoming-payments/{self.receipt_id}'
        for amount,expected in [(30,30),(20,50)]:
            response=await self.client.post(path+'/allocate',json={'allocations':[{'fee_record_id':self.fee_id,'is_refund':True,'amount':amount}]})
            self.assertEqual(response.status_code,200,response.text)
            async with self.sessions() as db:
                fee=await db.get(BusinessRecord,self.fee_id)
                self.assertEqual(fee.data['refunded_amount'],expected)
        response=await self.client.post(f'{API}/finance/incoming-payments/revoke-allocations',json={'payment_ids':[self.receipt_id]})
        self.assertEqual(response.status_code,200,response.text)
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,self.fee_id)
            self.assertEqual(fee.data['refunded_amount'],0)

    async def test_internal_fee_excluded_from_candidates_and_submission(self):
        path=f'{API}/finance/incoming-payments/{self.receipt_id}'
        response=await self.client.get(path+'/allocation-candidates')
        self.assertEqual(response.status_code,200,response.text)
        self.assertNotIn(self.internal_id,[row.get('fee_record_id') for row in response.json()['items']])
        response=await self.client.post(path+'/allocate',json={'allocations':[{'fee_record_id':self.internal_id,'amount':5}]})
        self.assertEqual(response.status_code,422,response.text)

    async def test_ordinary_receipt_cannot_impersonate_refund(self):
        async with self.sessions() as db:
            row=await db.get(IncomingPayment,self.receipt_id); row.payer_name='普通客户'; await db.commit()
        response=await self.client.post(f'{API}/finance/incoming-payments/{self.receipt_id}/allocate',json={'allocations':[{'fee_record_id':self.fee_id,'is_refund':True,'amount':20}]})
        self.assertEqual(response.status_code,422,response.text)

    async def test_grouping_happens_before_pagination(self):
        rows=[{'id':i,'status':'待结算','data':{'amount':amount,'payment_application_no':'request-a','case_no':'case','source_fee_id':7,'applicant':'tester'}} for i,amount in enumerate([2,5,5,5,10],1)]
        result=group_commission_applications(rows)
        self.assertEqual(len(result),1); self.assertEqual(result[0]['data']['amount'],27)
        self.assertEqual(len(result[0]['data']['application_items']),5)
        rows.append({'id':8,'status':'待结算','data':{**rows[0]['data'],'payment_application_no':'request-b'}})
        self.assertEqual(len(group_commission_applications(rows)),2)

    async def test_application_api_groups_real_stored_records(self):
        async with self.sessions() as db:
            for i,amount in enumerate([2,5,5,5,10]):
                db.add(self.record('finance',f'commission-{i}',{'fee_type':'内部费用','expense_scope':'内部','amount':amount,
                    'payment_application_no':'CODEX-0915-APPLICATION','case_no':'CODEX-0915-case','source_fee_id':self.fee_id,
                    'applicant':IDENTITY['username']},'待结算'))
            await db.commit()
        response=await self.client.get(f'{API}/finance/internal-fees',params={'scope':'applications','page_size':1})
        self.assertEqual(response.status_code,200,response.text)
        groups=[item for item in response.json()['items'] if item['serial_no']=='CODEX-0915-APPLICATION']
        self.assertEqual(len(groups),1,response.text)
        self.assertEqual(groups[0]['data']['amount'],27)
        self.assertEqual(groups[0]['data']['fee_type'],'内部费用')

    async def test_batch_submit_and_writeoff(self):
        async with self.sessions() as db:
            first=await db.get(BusinessRecord,self.fee_id)
            second=self.record('finance','second-fee',dict(first.data),'已审批')
            db.add(second); await db.commit(); second_id=second.id
        response=await self.client.post(f'{API}/finance/payment-workflow/submit-batch',json={'record_ids':[self.fee_id,second_id]})
        self.assertEqual(response.status_code,200,response.text)
        package_id=response.json()['id']
        response=await self.client.post(f'{API}/finance/payment-workflow/{package_id}/writeoff',data={
            'paid_date':str(date.today()),'amount':'200','payment_method':'现金','invoice_no':'BATCH-VOUCHER'},
            files=[('files',('proof.txt',b'CODEX-proof'))])
        self.assertEqual(response.status_code,200,response.text)
        async with self.sessions() as db:
            rows=[await db.get(BusinessRecord,i) for i in [self.fee_id,second_id]]
            self.assertTrue(all(row.status=='已付款' for row in rows))
            self.assertEqual(rows[0].data['invoice_record_id'],rows[1].data['invoice_record_id'])

    async def test_payment_permission_and_amount_rejection(self):
        self.app.dependency_overrides[current_identity]=lambda:{**IDENTITY,'role':'staff'}
        response=await self.client.post(f'{API}/finance/payment-workflow/{self.fee_id}/submit')
        self.assertEqual(response.status_code,403,response.text)
        self.app.dependency_overrides[current_identity]=lambda:IDENTITY
        await self.client.post(f'{API}/finance/payment-workflow/{self.fee_id}/submit')
        response=await self.client.post(f'{API}/finance/payment-workflow/{self.fee_id}/writeoff',data={
            'paid_date':str(date.today()),'amount':'1','payment_method':'现金','invoice_no':'TEST'},files=[('files',('proof.txt',b'proof'))])
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(list(Path(self.temp.name).rglob('*')),[])

    async def test_contract_payment_preserves_case_fee_voucher_link(self):
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,self.fee_id)
            payment=self.record('contract_payment','contract-payment',{**fee.data,'lines':[{'case_fee_id':fee.id,'amount':100,'case_no':fee.data['case_no']}]},'待付款')
            db.add(payment); await db.commit(); payment_id=payment.id
        path=f'{API}/finance/payment-workflow/{payment_id}'
        response=await self.client.post(path+'/submit')
        self.assertEqual(response.status_code,200,response.text)
        async with self.sessions() as db:
            from app.core.finance import _active_contract_payment_fee_reservations
            reserved=await _active_contract_payment_fee_reservations({self.fee_id},db)
            self.assertEqual(reserved[self.fee_id],100)
        response=await self.client.post(path+'/writeoff',data={'paid_date':str(date.today()),'amount':'100','payment_method':'银行卡','invoice_no':'CONTRACT-PROOF'},files=[('files',('proof.txt',b'proof'))])
        self.assertEqual(response.status_code,200,response.text)
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,self.fee_id)
            self.assertEqual(fee.data['invoice_no'],'CONTRACT-PROOF')
            self.assertTrue(fee.data['invoice_record_id'])


if __name__=='__main__': unittest.main()
