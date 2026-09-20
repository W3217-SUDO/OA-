"""9.18返工：真实前端请求与独立数据库持久化联测。"""
import json
import subprocess
import unittest
from pathlib import Path
from sqlalchemy import select, func
import finance_0916_batch_test as fixtures
from finance_0916_batch_test import API, IDENTITY
from app.models import BusinessRecord, WorkflowEvent, SystemParameter


class Rework0918Test(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.FinanceBatchTest.asyncSetUp
    asyncTearDown = fixtures.FinanceBatchTest.asyncTearDown

    async def test_actual_frontend_court_requests_and_atomic_validation(self):
        script = Path(__file__).with_name('caseRework0918.helpers.mjs')
        payloads = json.loads(subprocess.check_output(['node', str(script), '--payloads'], encoding='utf-8'))
        url = f'{API}/cases/{self.case_id}/court-info'
        saved = {}
        for level, body in zip(('first', 'second', 'execution', 'retrial'), payloads):
            response = await self.client.put(url, json=body)
            self.assertEqual(response.status_code, 200, response.text)
            saved[f'{level}_court_name'] = f'{level}法院'
            async with self.sessions() as db:
                case = await db.get(BusinessRecord, self.case_id)
                for key, value in saved.items():
                    self.assertEqual(case.data[key], value)
                before = dict(case.data)
                count = await db.scalar(select(func.count()).select_from(WorkflowEvent))
            response = await self.client.put(url, json={**body, f'{level}_court_name': ' '})
            self.assertEqual(response.status_code, 422, response.text)
            async with self.sessions() as db:
                self.assertEqual((await db.get(BusinessRecord, self.case_id)).data, before)
                self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), count)
            response = await self.client.put(url, json={f'{level}_court_filing_date': '2026-09-21'})
            self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            data = (await db.get(BusinessRecord, self.case_id)).data
            self.assertEqual(data['first_instance_court'], 'first法院')
            self.assertEqual(data['second_instance_court'], 'second法院')
            self.assertEqual(data['courtroom'], '法庭')

    async def test_clue_search_save_eligibility_and_failure_atomicity_both_entries(self):
        async with self.sessions() as db:
            db.add(SystemParameter(category='case_phase', code='CODEX-0918-phase', name='一审立案受理', is_active=True, extra={}))
            await db.commit()
        for case_type, entry in [('民事争议', 'normal-basic'), ('仲裁', 'arbitration-basic')]:
            async with self.sessions() as db:
                case = await db.get(BusinessRecord, self.case_id)
                case.data = {**case.data, 'case_type': case_type, 'first_court_name': '保留法院'}
                phase = case.status
                clues = []
                for suffix, state, customer, data in [('ok','已取证','Batch customer',{}), ('waiting','待审核','Batch customer',{}), ('other','已取证','Other',{}), ('used','已取证','Batch customer',{'converted_case_id':999})]:
                    item = BusinessRecord(module='clue', serial_no=f'CODEX-0918-{entry}-{suffix}', title=f'{entry}-{suffix}', customer=customer, owner=IDENTITY['username'], status=state, data=data)
                    db.add(item); clues.append(item)
                await db.commit()
                eligible, *invalid = [x.id for x in clues]
            response = await self.client.get(f'{API}/cases/{self.case_id}/clue-candidates', params={'keyword':entry})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual([x['id'] for x in response.json()['items']], [eligible])
            body = {'customer_record_id':self.customer_id,'title':'CODEX-0918-REWORK','case_phase':phase,'cause_or_charge':'案由','handling_lawyers':['Current manager'],'investigation_clue_ids':[eligible]}
            response = await self.client.put(f'{API}/cases/{self.case_id}/{entry}',json=body)
            self.assertEqual(response.status_code,200,response.text)
            async with self.sessions() as db:
                case=await db.get(BusinessRecord,self.case_id)
                self.assertEqual(case.data['investigation_clue_ids'],[eligible])
                self.assertEqual(case.data['first_court_name'],'保留法院')
                before=dict(case.data)
                count=await db.scalar(select(func.count()).select_from(WorkflowEvent))
            for invalid_id in invalid:
                response=await self.client.put(f'{API}/cases/{self.case_id}/{entry}',json={**body,'investigation_clue_ids':[eligible,invalid_id]})
                self.assertEqual(response.status_code,409,response.text)
                async with self.sessions() as db:
                    self.assertEqual((await db.get(BusinessRecord,self.case_id)).data,before)
                    self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)),count)
            # 阶段变化后的重新查询必须读取最新数据。
            async with self.sessions() as db:
                waiting=await db.get(BusinessRecord,invalid[0]);waiting.status='已取证';await db.commit()
            response=await self.client.get(f'{API}/cases/{self.case_id}/clue-candidates',params={'keyword':f'{entry}-waiting'})
            self.assertEqual([x['id'] for x in response.json()['items']],[invalid[0]])

if __name__ == '__main__':
    unittest.main()
