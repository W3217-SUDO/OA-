"""9.20与9.18追加问题：隔离数据库下的真实接口和持久化回归。"""
import unittest
from datetime import date, datetime, timedelta
from sqlalchemy import select
import finance_0916_batch_test as fixtures
from finance_0916_batch_test import API, IDENTITY
from app.models import BusinessRecord, User, Department, IncomingPayment, ReceivablePlan, HrSubrecord, JobRole
from fastapi import HTTPException
from app.core.system import _commission_employee_index
from app.core.tasks import _task_dict, _apply_task_auto_completion
from app.core.dashboard_scope import dashboard_identity, company_hearing_conditions
from app.core.case_department_scope import department_case_condition
from app.core.cases import _case_commission_preview_for_amount
from app.core.finance import _refund_case_fee_status


class September20BatchTest(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.FinanceBatchTest.asyncSetUp
    asyncTearDown = fixtures.FinanceBatchTest.asyncTearDown

    async def test_selected_allocation_cancel_persistence_and_stale_revision(self):
        async with self.sessions() as db:
            claimant=await db.scalar(select(User).where(User.username==IDENTITY['username']))
            claimant.display_name='管理者'
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, 'received_amount': 100, 'expense_subtype': '律师代理费（退费）'}
            plan = ReceivablePlan(contract_record_id=self.contract_id, phase='代理费', due_date=date.today(), amount=100, received_amount=100, status='已收款')
            db.add(plan); await db.flush()
            payment = IncomingPayment(receipt_no='CODEX-0920-selected', payer_name='payer', received_date=date.today(), amount=100, allocated_amount=100, operator=IDENTITY['username'], claimant=IDENTITY['username'], status='已分配', claimed_customer='Batch customer', allocations=[
                {'contract_id':self.contract_id, 'fee_record_id':self.fee_id, 'receivable_plan_id':plan.id, 'case_id':self.case_id, 'amount':30},
                {'contract_id':self.contract_id, 'fee_record_id':self.fee_id, 'receivable_plan_id':plan.id, 'case_id':self.case_id, 'amount':70},
            ])
            db.add(payment); await db.commit(); payment_id=payment.id; plan_id=plan.id
        path=f'{API}/finance/incoming-payments/{payment_id}/allocation-records'
        response=await self.client.get(path); self.assertEqual(response.status_code,200,response.text)
        data=response.json(); self.assertEqual(data['items'][0]['fee_type'],'律师代理费（退费）')
        self.assertEqual(data['items'][0]['fee_amount'],100)
        self.assertEqual(data['items'][0]['fee_received'],100)
        self.assertEqual(data['items'][0]['fee_remaining'],0)
        self.assertEqual(data['items'][0]['case_title'],'Batch case')
        self.assertEqual(data['payment']['claimant_display_name'],'管理者')
        payload={'revision':data['revision'],'indexes':[0]}
        response=await self.client.post(path+'/cancel',json=payload); self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['payment']['allocated_amount'],70)
        self.assertEqual(len(response.json()['items']),1)
        response=await self.client.post(path+'/cancel',json=payload); self.assertEqual(response.status_code,409,response.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord,self.fee_id)).data['received_amount'],70)
            self.assertEqual((await db.get(ReceivablePlan,plan_id)).received_amount,70)
            self.assertEqual((await db.get(IncomingPayment,payment_id)).status,'部分分配')

    async def test_allocation_candidates_show_specific_fee_type(self):
        async with self.sessions() as db:
            case=await db.get(BusinessRecord,self.case_id)
            case.data={**case.data,'contract_id':self.contract_id}
            fee=await db.get(BusinessRecord,self.fee_id)
            fee.data={**fee.data,'contract_id':self.contract_id,'expense_subtype':'律师代理费（退费）','received_amount':0}
            payment=IncomingPayment(receipt_no='CODEX-0920-candidate',payer_name='payer',received_date=date.today(),amount=100,allocated_amount=0,operator=IDENTITY['username'],claimant=IDENTITY['username'],status='待分配',claimed_customer='Batch customer',allocations=[])
            db.add(payment);await db.commit();payment_id=payment.id
        response=await self.client.get(f'{API}/finance/incoming-payments/{payment_id}/allocation-candidates',params={'case_fees_only':True})
        self.assertEqual(response.status_code,200,response.text)
        rows=[row for row in response.json()['items'] if row.get('fee_record_id')==self.fee_id]
        self.assertEqual(len(rows),1,response.text)
        self.assertEqual(rows[0]['fee_type'],'律师代理费（退费）')

    async def test_settled_receipt_cannot_cancel(self):
        async with self.sessions() as db:
            payment=await db.scalar(select(IncomingPayment).where(IncomingPayment.receipt_no=='CODEX-0916-receipt')); payment_id=payment.id
        path=f'{API}/finance/incoming-payments/{payment_id}/allocation-records'
        data=(await self.client.get(path)).json()
        response=await self.client.post(path+'/cancel',json={'revision':data['revision'],'indexes':[0]})
        self.assertEqual(response.status_code,409,response.text)
        async with self.sessions() as db: self.assertEqual((await db.get(IncomingPayment,payment_id)).allocated_amount,100)

    async def test_handoff_never_auto_completes_and_freezes_terminal_days(self):
        async with self.sessions() as db:
            task=BusinessRecord(module='task',serial_no='CODEX-0920-task',title='转交',owner=IDENTITY['username'],status='待接收',data={'deadline':str(date.today()-timedelta(days=30)), 'handoff_auto_complete_at':str(date.today()-timedelta(days=25)), 'case_no':'target', 'merged_from_case_no':'source'})
            db.add(task); await db.commit(); task_id=task.id
            await _apply_task_auto_completion(db); await db.refresh(task)
            self.assertEqual(task.status,'待接收'); self.assertEqual(_task_dict(task)['days_remaining'],-30)
            self.assertEqual(_task_dict(task)['status'],'已逾期'); self.assertIn('source',_task_dict(task)['case_nos'])
        response=await self.client.post(f'{API}/tasks/{task_id}/accept',json={}); self.assertEqual(response.status_code,200,response.text)
        async with self.sessions() as db:
            task=await db.get(BusinessRecord,task_id); task.status='已拒绝'; task.data={**task.data,'rejected_at':str(date.today()-timedelta(days=20))}; await db.commit()
            await db.refresh(task)
            self.assertEqual(_task_dict(task)['days_remaining'],-10)

    async def test_clue_conversion_optional_fields_and_default_system(self):
        async with self.sessions() as db:
            db.add(User(username='system', display_name='System', department='test', role='user', password_hash='unused', is_active=True))
            clue=BusinessRecord(module='clue',serial_no='CODEX-0920-clue',title='线索',owner=IDENTITY['username'],customer='Batch customer',status='已取证',data={'contract_record_id':self.contract_id})
            db.add(clue);await db.commit();clue_id=clue.id
        response=await self.client.post(API+'/investigations/clues/batch-cases',json={'clue_ids':[clue_id]})
        self.assertEqual(response.status_code,201,response.text);self.assertEqual(response.json()['created'],1,response.text)
        case_id=response.json()['created_ids'][0]
        async with self.sessions() as db:
            case=await db.get(BusinessRecord,case_id);self.assertEqual(case.status,'新案待分配');self.assertEqual(case.data['handling_lawyer_usernames'],['system']);self.assertFalse(case.data['assistant']);self.assertFalse(case.data['cause_or_charge'])
        response=await self.client.post(API+'/investigations/clues/batch-cases',json={'clue_ids':[clue_id]})
        self.assertEqual(response.json()['created'],0);self.assertEqual(response.json()['failed'],1)

    async def test_department_staff_relations_include_subdepartment_not_stamped_department(self):
        async with self.sessions() as db:
            dep=Department(code='CODEX-0920-dep',name='test'); db.add(dep); await db.flush()
            db.add(Department(code='CODEX-0920-child',name='child',parent_department_id=dep.id))
            db.add(User(username='CODEX-0920-child',display_name='child',department='child',role='user',password_hash='unused',is_active=True))
            case=await db.get(BusinessRecord,self.case_id); case.department='历史案件'; case.data={**case.data,'handling_lawyer_usernames':['CODEX-0920-child']}; await db.commit()
            condition=await department_case_condition(IDENTITY,db)
            ids=set((await db.scalars(select(BusinessRecord.id).where(BusinessRecord.module=='case',condition))).all())
            self.assertIn(self.case_id,ids)
            case.data={'assistant_username':'unrelated'}; await db.commit()
            ids=set((await db.scalars(select(BusinessRecord.id).where(BusinessRecord.module=='case',condition))).all()); self.assertNotIn(self.case_id,ids)

    async def test_owned_contract_adds_cases_but_excludes_merged(self):
        async with self.sessions() as db:
            user=User(username='CODEX-0920-owner',display_name='owner',department='test',role='user',password_hash='unused',is_active=True);db.add(user)
            contract=await db.get(BusinessRecord,self.contract_id);contract.owner=user.username
            case=await db.get(BusinessRecord,self.case_id);case.data={**case.data,'contract_id':self.contract_id};await db.commit()
            identity=await dashboard_identity({'username':user.username,'role':'user'},db);self.assertIn(self.case_id,identity['_dashboard_case_ids'])
            case.status='已合并';await db.commit()
            identity=await dashboard_identity({'username':user.username,'role':'user'},db);self.assertNotIn(self.case_id,identity['_dashboard_case_ids'])

    async def test_internal_schedule_and_external_department_boundary(self):
        async with self.sessions() as db:
            condition=await company_hearing_conditions(IDENTITY,db)
            ids=set((await db.scalars(select(BusinessRecord.id).where(*condition))).all());self.assertIn(self.case_id,ids)
            user=await db.scalar(select(User).where(User.username==IDENTITY['username']));user.department='外部合作调查取证部';await db.commit()
            condition=await company_hearing_conditions(IDENTITY,db)
            self.assertEqual(list((await db.scalars(select(BusinessRecord.id).where(*condition))).all()),[])

    async def test_source_and_quality_same_person_get_distinct_commissions(self):
        async with self.sessions() as db:
            scheme=await db.scalar(select(HrSubrecord));scheme.data={**scheme.data,'source_rate':.05,'quality_rate':.02}
            case=await db.get(BusinessRecord,self.case_id); await db.commit()
            preview=await _case_commission_preview_for_amount(case,100,db,quality_manager_tokens=[IDENTITY['username']])
            roles={item['commission_role'] for item in preview['items']}
            self.assertIn('案源',roles);self.assertIn('品管',roles)

    async def test_refund_progress_codes_and_days(self):
        names=['准备材料','客户盖章','已提交法院','待法院现场办理','退费到客户','回款待分配']
        for code,name in zip(['R10','R20','R30','R35','R40','R50'],names):
            self.assertEqual(_refund_case_fee_status({'legacy_record':{'RefundStatus':int(code[1:])}}),(code,name))
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,self.fee_id);fee.data={**fee.data,'refund_requested_amount':50,'refund_status':'R20','refund_status_label':'客户盖章','refund_status_started_at':str(date.today()-timedelta(days=30))};await db.commit()
        response=await self.client.get(API+'/finance/case-fees/refunds',params={'refund_status':'客户盖章'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['items'][0]['data']['refund_progress_days'],30)
        response=await self.client.post(API+'/finance/case-fees/refunds/status',json={'ids':[self.fee_id],'status':'R30','comment':'核对'})
        self.assertEqual(response.status_code,200,response.text)
        async with self.sessions() as db:
            data=(await db.get(BusinessRecord,self.fee_id)).data;self.assertEqual(data['refund_status_label'],'已提交法院');self.assertEqual(data['refund_status_started_at'][:10],str(date.today()))

    async def test_employee_binding_explicit_unlink_preserves_manager(self):
        async with self.sessions() as db:
            employee=await db.scalar(select(BusinessRecord).where(BusinessRecord.module=='hr'))
            duplicate=BusinessRecord(module='hr',serial_no='CODEX-0920-duplicate',title='另一人员',owner='another',data={'username':IDENTITY['username']})
            db.add(duplicate);await db.commit()
            self.assertIsNone((await _commission_employee_index(db))[IDENTITY['username'].lower()])
            duplicate.data={**duplicate.data,'username':''};await db.commit()
            self.assertEqual((await _commission_employee_index(db))[IDENTITY['username'].lower()].id,employee.id)

    async def test_missing_quality_scheme_keeps_person_and_returns_notice(self):
        async with self.sessions() as db:
            username='CODEX-0920-quality'
            db.add(User(username=username,display_name='管理者',department='test',role='user',password_hash='unused',is_active=True))
            db.add(BusinessRecord(module='hr',serial_no='CODEX-0920-quality-hr',title='管理者',owner=username,data={'username':username}))
            await db.commit()
            case=await db.get(BusinessRecord,self.case_id)
            preview=await _case_commission_preview_for_amount(case,100,db,quality_manager_tokens=[username])
            self.assertTrue(any(item['role']=='品管' and item['username']==username for item in preview['personnel']))
            self.assertTrue(any('管理者（品管）' in text and '未配置' in text for text in preview['scheme_messages']))
            self.assertFalse(any(item['commission_role']=='品管' for item in preview['items']))
            self.assertTrue(any(item['commission_role']=='开庭' for item in preview['items']))

    async def test_nonadmin_department_permission_is_required(self):
        async with self.sessions() as db:
            db.add(Department(code='CODEX-0920-permission-dep',name='test'))
            role=JobRole(code='CODEX-0920-role',name='部门角色',permissions=['case-dept'],is_active=True)
            user=User(username='CODEX-0920-reader',display_name='reader',department='test',role='user',password_hash='unused',is_active=True,profile={'permission_role_code':role.code})
            db.add_all([role,user]);await db.commit()
            condition=await department_case_condition({'username':user.username,'role':'user'},db)
            ids=set((await db.scalars(select(BusinessRecord.id).where(BusinessRecord.module=='case',condition))).all())
            self.assertIn(self.case_id,ids)
            role.permissions=[];await db.commit()
            with self.assertRaises(HTTPException) as caught:
                await department_case_condition({'username':user.username,'role':'user'},db)
            self.assertEqual(caught.exception.status_code,403)

if __name__=='__main__':unittest.main()
