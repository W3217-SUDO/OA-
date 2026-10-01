"""9.29 行13、20–26隔离API与持久化验证，不进入生产源码或构建。"""
import asyncio
import json
import os
from datetime import date, timedelta
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(os.environ['OA_929_CLUES_EVIDENCE_DIR']).resolve()
assert not ROOT.is_relative_to(REPO), '验证资料必须位于源码及构建目录之外'
ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / 'apps' / 'api-server'))
os.environ.update(DATABASE_URL=f'sqlite+aiosqlite:///{(ROOT / "clues-test.db").as_posix()}',
                  UPLOAD_ROOT=str(ROOT / 'clues-uploads'), SEED_DEMO_DATA='false',
                  DINGTALK_NOTIFICATIONS_ENABLED='false', PYTHONDONTWRITEBYTECODE='1')
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select
from app.database import Base, engine, SessionLocal
from app.main import app
from app.models import BusinessRecord, FileAttachment, JobRole, RolePermission, SystemConfig, User, Warehouse, WarehouseStorageLocation, WorkflowEvent
from app.security import create_token, hash_password
from app.core.constants import FIELD_KEYS

PREFIX = 'CODEX-929-'
checks = []
requests = []
ids = {}

def check(name, value, detail=None):
    assert value, f'{name}: {detail}'
    checks.append({'name': name, 'passed': True})
    print('PASS', name, flush=True)

def record(module, name, owner='collector', data=None, status='待审批', customer='CODEX-929-客户甲'):
    return BusinessRecord(module=module, serial_no=PREFIX + name, title=PREFIX + name,
                          customer=customer, owner=PREFIX + owner, department='CODEX-929-部门',
                          status=status, data=data or {}, description='隔离验证')

async def seed():
    assert str(engine.url.database) == str(ROOT / 'clues-test.db').replace('\\', '/')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        db.add_all([
            RolePermission(role='user', display_name='隔离普通人员', data_scope='本人及共享数据',
                           menu_keys=['investigation', 'case-mine', 'case-mine-schedule', 'contract-mine', 'finance'], field_keys=list(FIELD_KEYS)),
            RolePermission(role='manager', display_name='隔离全所人员', data_scope='全所数据',
                           menu_keys=['investigation', 'case-mine', 'finance'], field_keys=list(FIELD_KEYS)),
            JobRole(code='CODEX-929-FINANCE', name='财务审核管理', is_active=True,
                    permissions=['finance'], data_scope='全所数据'),
            SystemConfig(key='investigation_assignment', label='调查任务分配', value={'supervisor_username': PREFIX+'supervisor'}),
        ])
        password = hash_password('CODEX-929-Test-Only')
        for username in ['admin', 'brand', 'brand2', 'brand_foo', 'collector', 'other', 'supervisor', 'supervisor2', 'finance']:
            role = 'admin' if username == 'admin' else 'manager' if username == 'finance' else 'user'
            db.add(User(username=PREFIX+username, display_name=PREFIX+username, role=role, role_ids=[role],
                        department='CODEX-929-部门', password_hash=password, is_active=True,
                        profile={'permission_role': '财务审核管理'} if username == 'finance' else {}))
        customer = record('customer', 'R21-CUSTOMER', owner='brand', data={'customer_managers': [PREFIX+'brand']}, status='合作客户')
        other_customer = record('customer', 'R21-OTHER-CUSTOMER', owner='other', data={'customer_managers': [PREFIX+'other',PREFIX+'brandxfoo']}, status='合作客户', customer='CODEX-929-客户乙')
        db.add_all([customer, other_customer]); await db.flush()
        ids.update(customer=customer.id, other_customer=other_customer.id)
        contract = record('contract', 'R13-CONTRACT', owner='admin', status='审批通过', data={'customer_id': customer.id, 'customer_no': customer.serial_no})
        db.add(contract); await db.flush(); ids['contract'] = contract.id
        parent = record('investigation', 'R21-PARENT', owner='supervisor', status='进行中', data={'customer_id': customer.id, 'contract_id': contract.id})
        parent2 = record('investigation', 'R21-OTHER-PARENT', owner='supervisor', status='进行中', data={'customer_id': other_customer.id})
        db.add_all([parent, parent2]); await db.flush(); ids['parent'] = parent.id
        tasks = [record('task', f'R21-TASK-{i}', status='进行中', data={'investigation_record_id': parent.id, 'contract_id': contract.id}) for i in range(2)]
        db.add_all(tasks); await db.flush(); ids['task'] = tasks[0].id
        clue1 = record('clue', 'R21-CLUE-1', data={'source_task_id': tasks[0].id, 'investigation_record_id': parent.id, 'customer_managers': []})
        clue2 = record('clue', 'R21-CLUE-2', data={'source_task_id': tasks[1].id, 'customer_managers': [], 'customer_review': True})
        other = record('clue', 'R21-OTHER-CLUE', data={'investigation_record_id': parent2.id}, customer='CODEX-929-客户乙')
        db.add_all([clue1, clue2, other]); await db.flush()
        ids.update(clue1=clue1.id, clue2=clue2.id, other=other.id)
        evidence = record('evidence', 'R21-EVIDENCE', status='待整理', data={'clue_id': clue1.id})
        sibling = record('evidence', 'R21-SIBLING-EVIDENCE', status='待整理', data={'clue_id': clue2.id})
        db.add_all([evidence, sibling]); await db.flush(); ids['evidence'] = evidence.id
        file_path = ROOT / 'clues-uploads' / 'CODEX-929-R21.txt'; file_path.parent.mkdir(exist_ok=True); file_path.write_text('CODEX-929-真实附件正文', encoding='utf-8')
        attachment = FileAttachment(record_id=evidence.id, category='取证文件', original_name=file_path.name, stored_name=file_path.name,
                                    content_type='text/plain', size=file_path.stat().st_size, path=str(file_path), uploader=PREFIX+'collector')
        db.add(attachment); await db.flush(); ids['attachment'] = attachment.id
        warehouse = Warehouse(warehouse_no='CODEX-929-R23-W', name='CODEX仓库'); db.add(warehouse); await db.flush()
        location = WarehouseStorageLocation(warehouse_id=warehouse.id, storage_location_no='CODEX-929-R23-L', name='CODEX库位')
        db.add(location); await db.flush(); ids.update(warehouse=warehouse.id, location=location.id)
        own_case = record('case', 'R25-OWN-CASE', owner='finance', status='一审准备开庭', data={'assistant_username': PREFIX+'finance'})
        other_case = record('case', 'R25-OTHER-CASE', owner='other', status='一审准备开庭', data={'assistant_username': PREFIX+'other'})
        db.add_all([own_case, other_case]); await db.flush(); ids.update(own_case=own_case.id, other_case=other_case.id)
        for case in [own_case, other_case]:
            fee = record('finance', f'R25-FEE-{case.id}', owner='admin', status='已支付', data={'case_id': case.id, 'case_no': case.serial_no,
                         'fee_category': 'official', 'fee_group': 'official', 'fee_type': '一审诉讼费', 'amount': 100, 'paid_amount': 100,
                         'refund_requested_amount': 50, 'refund_status': 'R10'})
            db.add(fee)
        await db.commit()

async def main():
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://isolated.local') as client:
        async def request(method, path, user='admin', expected=200, **kwargs):
            role = 'admin' if user == 'admin' else 'manager' if user == 'finance' else 'user'
            response = await client.request(method, '/api/v1'+path, headers={'Authorization': 'Bearer '+create_token(PREFIX+user, role)}, **kwargs)
            assert response.status_code == expected, (method, path, response.status_code, response.text[:1600])
            requests.append({'method':method,'path':path,'user':user,'status':expected})
            return response

        query = {'module':'clue', 'scope':'audit', 'statuses':'待审批', 'page_size':1}
        first = (await request('GET', '/records', 'brand', params=query)).json()
        second = (await request('GET', '/records', 'brand', params={**query, 'page':2})).json()
        check('R21 品牌管理员无岗位权限仍见两任务线索且分页总数一致', first['total']==second['total']==2 and first['items'][0]['id']!=second['items'][0]['id'], [first,second])
        ordinary = (await request('GET','/records','collector',params=query)).json()
        check('R21 本人上传不等于有品牌审批权', ordinary['total']==0)
        wildcard=(await request('GET','/records','brand_foo',params=query)).json()
        check('R21 用户名含下划线仍为精确成员匹配',wildcard['total']==0)
        await request('GET',f'/records/{ids["other"]}','brand',expected=403,params={'scope':'audit'})
        cap = (await request('GET','/investigations/action-capabilities','brand',params={'scope':'audit','record_ids':f'{ids["clue1"]},{ids["clue2"]},{ids["other"]}'})).json()['items']
        check('R21 操作权限与列表同源', len(cap)==2 and all(v['review_clue'] for v in cap.values()),cap)
        async with SessionLocal() as db:
            clue=await db.get(BusinessRecord,ids['clue2']); clue.data={**clue.data,'reviewer':PREFIX+'other'}; await db.commit()
        await request('POST',f'/investigations/clues/{ids["clue2"]}/review','brand',expected=403,json={'approved':True,'comment':'CODEX-929-指定审核人拒绝'})
        assigned=(await request('GET','/investigations/action-capabilities','brand',params={'scope':'audit','record_ids':str(ids['clue2'])})).json()['items']
        check('R21 品牌权限仍遵守指定审核人',not assigned[str(ids['clue2'])]['review_clue'])
        async with SessionLocal() as db:
            clue=await db.get(BusinessRecord,ids['clue2']); clue.data={**clue.data,'reviewer':''}; await db.commit()
        sql=[]
        def capture(_conn,_cursor,statement,_parameters,_context,_executemany):
            sql.append(statement)
        event.listen(engine.sync_engine,'before_cursor_execute',capture)
        await request('GET','/records','brand',params={**query,'page_size':1}); small=len(sql); sql.clear()
        await request('GET','/records','brand',params={**query,'page_size':100}); large=len(sql)
        event.remove(engine.sync_engine,'before_cursor_execute',capture)
        check('R21 页大小变化不产生逐条关系查询',large==small,{'small':small,'large':large})
        workspace = (await request('GET',f'/investigations/clues/{ids["clue1"]}/workspace','brand',params={'scope':'audit'})).json()
        check('R21 workspace 不串兄弟任务证据', len(workspace['evidence'])==1 and workspace['evidence'][0]['id']==ids['evidence'],workspace.keys())
        downloaded = await request('GET',f'/attachments/{ids["attachment"]}/download','brand')
        check('R21 品牌审核可读真实附件', '真实附件正文' in downloaded.text)
        await request('DELETE',f'/attachments/{ids["attachment"]}','brand',expected=403)
        await request('POST','/attachments','brand',expected=404,data={'record_id':str(ids['evidence']),'category':'取证文件'},files={'file':('CODEX-929-forbidden.txt',b'forbidden','text/plain')})
        uploaded=(await request('POST','/attachments','collector',expected=201,data={'record_id':str(ids['evidence']),'category':'取证文件'},files={'file':('CODEX-929-owner.txt',b'owner-evidence','text/plain')})).json()
        check('R21 品牌只读不授上传删除，负责人正常上传',uploaded['record_id']==ids['evidence'])
        exported = await request('GET','/investigations/clues/export','brand',params={'scope':'audit','statuses':'待审批'})
        check('R21 导出无越权客户', 'R21-CLUE-1' in exported.text and 'OTHER-CLUE' not in exported.text)
        await request('POST',f'/investigations/clues/{ids["other"]}/review','brand',expected=403,json={'approved':True,'comment':'CODEX-929-审批'})
        reviewed = (await request('POST',f'/investigations/clues/{ids["clue1"]}/review','brand',json={'approved':True,'comment':'CODEX-929-R21通过'})).json()
        check('R21 不需客户审核时审批后待取证',reviewed['status']=='待取证')
        history=(await request('GET','/records','brand',params={**query,'statuses':'待取证'})).json()
        check('R21 审批完成后对应历史标签仍可查看',history['total']==1 and history['items'][0]['id']==ids['clue1'])
        await request('GET',f'/records/{ids["clue1"]}','brand',params={'scope':'audit'})
        async with SessionLocal() as db:
            customer = await db.get(BusinessRecord,ids['customer']); customer.data={**customer.data,'customer_managers':[PREFIX+'brand2']}; customer.owner=PREFIX+'brand2'; await db.commit()
        revoked=(await request('GET','/records','brand',params=query)).json()
        check('R21 转移品牌后旧管理员即时收回',revoked['total']==0)
        await request('GET',f'/attachments/{ids["attachment"]}/download','brand',expected=404)
        await request('GET',f'/attachments/{ids["attachment"]}/download','collector')
        await request('POST',f'/investigations/clues/{ids["clue2"]}/review','brand',expected=403,json={'approved':True,'comment':'CODEX-929-审批'})
        approved=(await request('POST',f'/investigations/clues/{ids["clue2"]}/review','brand2',json={'approved':True,'comment':'CODEX-929-审核'})).json()
        check('R21 客户审核仍为独立下一阶段',approved['status']=='待客户审核')
        await request('POST',f'/investigations/clues/{ids["clue2"]}/customer-review','brand2',json={'approved':False,'comment':'CODEX-929-拒绝'})

        await request('PATCH','/system/configs/investigation_assignment','brand',expected=403,json={'value':{'supervisor_username':PREFIX+'brand'}})
        await request('PATCH','/system/configs/investigation_assignment',json={'value':{'supervisor_username':PREFIX+'supervisor2'}})
        actual=(await request('GET','/investigations/assignment-supervisor')).json()
        check('R13 主管配置持久化到创建读取同源',actual['username']==PREFIX+'supervisor2')
        create_body={'title':'CODEX-929-R13-新调查','authorized_from':str(date.today()),'authorized_to':str(date.today()+timedelta(days=30)),'right_type':'商标'}
        created=(await request('POST',f'/contracts/{ids["contract"]}/investigation',expected=201,json=create_body)).json()
        check('R13 合同真实入口使用新主管',created['owner']==PREFIX+'supervisor2',created)
        await request('PATCH','/system/configs/investigation_assignment',json={'value':{'supervisor_username':''}})
        await request('GET','/investigations/assignment-supervisor',expected=409)
        await request('PATCH','/system/configs/investigation_assignment',expected=422,json={'value':{'supervisor_username':'CODEX-929-不存在'}})
        await request('POST','/investigations/records',expected=409,json={'module':'investigation','serial_no':'CODEX-929-R13-CLEAR','title':'CODEX-929-无主管','data':{'contract_id':ids['contract']}})
        await request('PATCH','/system/configs/investigation_assignment',json={'value':{'supervisor_username':PREFIX+'supervisor'}})
        async with SessionLocal() as db:
            prior=await db.get(BusinessRecord,ids['parent']); check('R13 更换配置不重分配历史任务',prior.owner==PREFIX+'supervisor')

        channel_clues=[]
        for channel in ['阿里巴巴','苏宁','1号店']:
            item=(await request('POST','/investigations/records',expected=201,json={'module':'clue','serial_no':'ignored','title':'CODEX-929-R20-'+channel,'data':{'source_task_id':ids['task'],'sales_channel':channel,'platform':channel,'product':'CODEX-929-商品'}})).json()
            channel_clues.append(item['id'])
            check('R20 渠道保存 '+channel,item['data']['sales_channel']==channel and item['data']['customer_id']==ids['customer'])
        target=channel_clues[0]
        payload={'clue_ids':[target], 'handling_lawyer':PREFIX+'admin','case_type':'民事争议','cause_or_charge':'商标侵权'}
        result=(await request('POST','/investigations/clues/batch-cases',expected=201,json=payload)).json()
        check('R23 草稿不能生成案件',result['created']==0 and result['failed']==1,result)
        await request('POST',f'/investigations/clues/{target}/submit',json={'comment':'CODEX-929-R23提交'})
        result=(await request('POST','/investigations/clues/batch-cases',expected=201,json=payload)).json()
        check('R23 待审批不能生成案件',result['created']==0 and result['failed']==1)
        await request('POST',f'/investigations/clues/{target}/review',json={'approved':True,'comment':'CODEX-929-审批'})
        result=(await request('POST','/investigations/clues/batch-cases',expected=201,json=payload)).json()
        check('R23 待取证不能生成案件',result['created']==0 and result['failed']==1)
        await request('PATCH',f'/investigations/records/{target}',expected=409,json={'status':'已取证'})
        await request('POST',f'/investigations/clues/{target}/collect',json={'collected_at':str(date.today()),'notary_institution':'公证处','warehouse_id':ids['warehouse'],'storage_location_id':ids['location']})
        result=(await request('POST','/investigations/clues/batch-cases',expected=201,json=payload)).json()
        check('R23 真实登记取证后生成成功',result['created']==1,result)
        result=(await request('POST','/investigations/clues/batch-cases',expected=201,json=payload)).json()
        check('R23 重复转案阻断',result['created']==0 and result['failed']==1)
        target=channel_clues[1]
        await request('POST',f'/investigations/clues/{target}/submit',json={})
        await request('POST',f'/investigations/clues/{target}/review',json={'approved':True,'comment':'CODEX-929-审批'})
        await request('POST',f'/investigations/clues/{target}/collect',json={'collected_at':str(date.today()),'notary_institution':'公证处','warehouse_id':ids['warehouse'],'storage_location_id':ids['location']})
        await request('POST',f'/investigations/{target}/notary',expected=201)
        result=(await request('POST','/investigations/clues/batch-cases',expected=201,json={**payload,'clue_ids':[target]})).json()
        check('R23 正常已取证后待公证链可生成',result['created']==1,result)
        historical=channel_clues[2]
        async with SessionLocal() as db:
            clue=await db.get(BusinessRecord,historical)
            case=await db.get(BusinessRecord,ids['own_case'])
            clue.data={**clue.data,'case_id':case.id,'case_no':case.serial_no,'converted_case_id':case.id,'converted_case_no':case.serial_no}
            case.data={**case.data,'clue_ids':[historical],'merged_sources':[{'data':{'clue_id':historical}}]}
            await db.commit()
        await request('POST',f'/investigations/clues/{historical}/submit',json={'comment':'CODEX-929-历史关联重提'})
        result=(await request('POST','/investigations/clues/batch-cases',expected=201,json={**payload,'clue_ids':[historical]})).json()
        async with SessionLocal() as db:
            clue=await db.get(BusinessRecord,historical); case=await db.get(BusinessRecord,ids['own_case'])
            check('R23 重提待审批不新增案件且保留历史合并关系',result['created']==0 and clue.data['converted_case_id']==case.id and case.data['merged_sources'][0]['data']['clue_id']==historical)

        personal=(await request('GET','/finance/case-fees/refunds','finance',params={'dashboard_queue':'refund-pending'})).json()
        company=(await request('GET','/finance/case-fees/refunds','finance')).json()
        check('R25 个人只含本人参与而公司查询保留全量',personal['total']==1 and company['total']==2,[personal,company])
        card=(await request('GET','/dashboard/personal-queues/refund-pending','finance')).json()
        check('R25 个人卡片列表数量一致',card['total']==personal['total'],card)
        export=await request('GET','/finance/case-fees/refunds/export','finance',params={'dashboard_queue':'refund-pending'})
        check('R25 个人导出排除无关案件','R25-OWN-CASE' in export.text and 'R25-OTHER-CASE' not in export.text)
        admin_company=(await request('GET','/finance/case-fees/refunds')).json()
        check('R25 管理员公司入口保持全量',admin_company['total']==2)
        async with SessionLocal() as db:
            persisted=await db.get(BusinessRecord,channel_clues[2]); check('R20 新会话读回渠道',persisted.data['sales_channel']=='1号店')
            rejected=await db.get(BusinessRecord,ids['clue2']); check('R21 拒绝状态及意见落库',rejected.status=='已驳回' and rejected.data['customer_review_comment']=='CODEX-929-拒绝')
            denied=await db.get(BusinessRecord,ids['other']); check('R21 越权操作无状态写入',denied.status=='待审批')
            count=await db.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.record_id==ids['clue1']))
            check('R21 审核日志持久化',count>=1)
    (ROOT/'clues-test-results.json').write_text(json.dumps({'checks':checks,'count':len(checks),'requests':requests,'database':str(ROOT/'clues-test.db')},ensure_ascii=False,indent=2),encoding='utf-8')

async def cleanup():
    # 仅清理本脚本专属外部数据库及上传目录，保留结果和日志。
    assert Path(engine.url.database).resolve() == ROOT / 'clues-test.db'
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        counts={model.__tablename__:await db.scalar(select(func.count()).select_from(model)) for model in (BusinessRecord,User,FileAttachment,WorkflowEvent)}
        assert all(count==0 for count in counts.values())
    upload_root=ROOT/'clues-uploads'
    files=list(upload_root.rglob('*')) if upload_root.exists() else []
    for item in sorted(files,key=lambda value:len(value.parts),reverse=True):
        assert item.resolve().is_relative_to(upload_root.resolve())
        item.unlink() if item.is_file() else item.rmdir()
    (ROOT/'clues-cleanup.json').write_text(json.dumps({'counts':counts,'remaining_upload_files':len(list(upload_root.rglob('*'))) if upload_root.exists() else 0,'ports_started':[]},ensure_ascii=False,indent=2),encoding='utf-8')
    await engine.dispose()

async def run():
    try:
        await main()
    finally:
        await cleanup()

if __name__=='__main__':
    asyncio.run(run())
