"""第9、10行接口回归：隔离内存库，核对关系、权限和持久化。"""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import select
from finance_0916_batch_test import FinanceBatchTest, API, IDENTITY, app, current_identity
from app.models import BusinessRecord, FileAttachment, User


class CaseDocumentsTest(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = FinanceBatchTest.asyncSetUp
    asyncTearDown = FinanceBatchTest.asyncTearDown

    async def test_nested_merge_combines_history_contracts_folders_and_same_names(self):
        with tempfile.TemporaryDirectory(prefix='CODEX-0918-merged-docs-') as directory:
            root = Path(directory)
            async with self.sessions() as db:
                main = await db.get(BusinessRecord, self.case_id)
                cases = [main]
                for index in range(2):
                    case = BusinessRecord(module='case', serial_no=f'CODEX-0918-history-{index}',
                        title='历史案件', customer=main.customer, owner=IDENTITY['username'],
                        status='一审准备开庭', data={'case_type': '民事争议'})
                    db.add(case)
                    cases.append(case)
                await db.flush()
                files = []
                for index, case in enumerate(cases):
                    contract = BusinessRecord(module='contract', serial_no=f'CODEX-0918-history-contract-{index}',
                        title='历史合同', customer=main.customer, owner=IDENTITY['username'], data={})
                    db.add(contract)
                    await db.flush()
                    case.data = {**case.data, 'contract_id': contract.id,
                        'custom_case_document_folders': [f'历史目录{index}']}
                    for record, category in ((case, f'历史目录{index}'), (contract, '合同附件')):
                        path = root / f'{record.id}.txt'
                        path.write_bytes(str(record.id).encode())
                        files.append(FileAttachment(record_id=record.id, category=category,
                            original_name='同名历史文件.txt', stored_name=path.name, path=str(path),
                            size=path.stat().st_size, uploader=IDENTITY['username'], content_type='text/plain'))
                db.add_all(files)
                await db.commit()
                ids = [case.id for case in cases]
                nos = [case.serial_no for case in cases]
                expected_ids = {file.id for file in files}
            response = await self.client.post(f'{API}/cases/{ids[1]}/merge', json={'source_case_no': nos[2]})
            self.assertEqual(response.status_code, 200, response.text)
            response = await self.client.post(f'{API}/cases/{ids[0]}/merge', json={'source_case_no': response.json()['target']['serial_no']})
            self.assertEqual(response.status_code, 200, response.text)
            ids[0] = response.json()['target']['id']
            listed = await self.client.get(f'{API}/cases/{ids[0]}/documents', params={'page_size': 2})
            items = listed.json()['items']
            for page in range(2, listed.json()['pages'] + 1):
                response = await self.client.get(f'{API}/cases/{ids[0]}/documents', params={'page_size': 2, 'page': page})
                items.extend(response.json()['items'])
            self.assertEqual({item['id'] for item in items}, expected_ids)
            self.assertEqual(len(items), 6)
            self.assertEqual(sum(item['document_category'] == '合同文档' for item in items), 3)
            folders = await self.client.get(f'{API}/cases/{ids[0]}/document-folders')
            self.assertTrue(all(f'历史目录{i}' in folders.json()['folders'] for i in range(3)))
            with patch('app.core.storage.UPLOAD_ROOT', root):
                for item in items:
                    response = await self.client.get(f"{API}/attachments/{item['id']}/download")
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertTrue(response.content)
            async with self.sessions() as db:
                self.assertEqual(len((await db.scalars(select(FileAttachment))).all()), 6)
        self.assertFalse(root.exists())

    async def seed(self, count=1):
        async with self.sessions() as db:
            clue = BusinessRecord(module="clue", serial_no="CODEX-0917-clue", title="线索", owner=IDENTITY['username'], data={})
            investigation = BusinessRecord(module="investigation", serial_no="CODEX-0917-investigation", title="调查", owner=IDENTITY['username'], data={})
            other = BusinessRecord(module="clue", serial_no="CODEX-0917-other", title="无关线索", owner=IDENTITY['username'], data={'converted_case_id':self.case_id})
            db.add_all([clue,investigation,other]);await db.flush()
            evidence = BusinessRecord(module="evidence", serial_no="CODEX-0917-evidence", title="取证", owner=IDENTITY['username'], data={'clue_id':clue.id})
            db.add(evidence);await db.flush()
            clue.data={'investigation_record_id':investigation.id,'collection_evidence_record_id':evidence.id}
            case=await db.get(BusinessRecord,self.case_id);case.data={**case.data,'investigation_clue_ids':[clue.id],'clue_record_id':clue.id,'investigation_clue_nos':[clue.serial_no]}
            files=[]
            for index in range(count):
                files.append(FileAttachment(record_id=clue.id,category='调查线索附件',original_name=f'{index}.txt',stored_name=f'CODEX-0917-{index}',path='isolated-unused',size=1,uploader=IDENTITY['username']))
            for record,category in [(clue,'取证文件'),(evidence,'普通附件'),(investigation,'普通附件'),(case,'案件资料'),(other,'调查线索附件')]:
                files.append(FileAttachment(record_id=record.id,category=category,original_name=f'{record.id}-{category}.txt',stored_name=f'CODEX-0917-{record.id}-{category}',path='isolated-unused',size=1,uploader=IDENTITY['username']))
            db.add_all(files);await db.commit()
            self.clue_id=clue.id;self.clue_no=clue.serial_no;self.excluded_id=files[-1].id
            self.before={item.id:(item.record_id,item.category,item.path) for item in files}

    async def test_related_files_classification_paging_and_no_mutation(self):
        await self.seed(201)
        path=f'{API}/cases/{self.case_id}/documents'
        first=await self.client.get(path);self.assertEqual(first.status_code,200,first.text)
        second=await self.client.get(path,params={'page':2})
        items=first.json()['items']+second.json()['items']
        self.assertEqual(first.json()['total'],205);self.assertEqual(len(items),205)
        self.assertEqual(len({row['id'] for row in items}),205)
        self.assertNotIn(self.excluded_id,{row['id'] for row in items})
        self.assertEqual(sum(row['document_category']=='调查文档' for row in items),201)
        self.assertEqual(sum(row['document_category']=='取证文档' for row in items),2)
        self.assertEqual(sum(row['document_category']=='鉴别资料' for row in items),1)
        for item in items:
            metadata=await self.client.get(f"{API}/attachments/{item['id']}")
            self.assertEqual(metadata.status_code,200,metadata.text)
        async with self.sessions() as db:
            after={item.id:(item.record_id,item.category,item.path) for item in (await db.scalars(select(FileAttachment))).all()}
        self.assertEqual(self.before,after)

    async def test_clue_workspace_and_serial_relation(self):
        await self.seed()
        workspace=await self.client.get(f'{API}/investigations/clues/{self.clue_id}/workspace')
        self.assertEqual(workspace.status_code,200,workspace.text)
        self.assertEqual(len(workspace.json()['clue_files']),2)
        self.assertEqual(len(workspace.json()['evidence']),1)
        async with self.sessions() as db:
            case=await db.get(BusinessRecord,self.case_id)
            case.data={**case.data,'investigation_clue_ids':[],'clue_record_id':None}
            await db.commit()
        result=await self.client.get(f'{API}/cases/{self.case_id}/documents')
        self.assertEqual(result.json()['total'],5)

    async def test_empty_and_unauthorized(self):
        result=await self.client.get(f'{API}/cases/{self.case_id}/documents')
        self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['total'],0)
        await self.seed()
        async with self.sessions() as db:
            db.add(User(username='CODEX-0917-outsider',display_name='无关人员',role='user',department='other',password_hash='unused',is_active=True));await db.commit()
        app.dependency_overrides[current_identity]=lambda:{'username':'CODEX-0917-outsider','role':'user'}
        for path in [f'/cases/{self.case_id}/documents',f'/investigations/clues/{self.clue_id}/workspace']:
            result=await self.client.get(API+path)
            self.assertIn(result.status_code,[403,404],result.text)

    async def test_new_conversion_keeps_original_file_and_download(self):
        await self.seed()
        async with self.sessions() as db:
            clue=await db.get(BusinessRecord,self.clue_id)
            contract=await db.get(BusinessRecord,self.contract_id)
            clue.status='已取证';clue.customer=contract.customer
            clue.data={**clue.data,'contract_id':contract.id}
            await db.commit()
        created=await self.client.post(f'{API}/investigations/clues/batch-cases',json={
            'clue_ids':[self.clue_id],'case_type':'民事案件','cause_or_charge':'侵害商标权纠纷',
            'handling_lawyer':IDENTITY['username'],'assistant':IDENTITY['username'],
        })
        self.assertEqual(created.status_code,201,created.text)
        self.assertEqual(created.json()['created'],1,created.text)
        case_id=created.json()['created_ids'][0]
        listed=await self.client.get(f'{API}/cases/{case_id}/documents')
        self.assertEqual(listed.json()['total'],4,listed.text)
        item=next(row for row in listed.json()['items'] if row['document_category']=='调查文档')
        self.assertEqual(item['record_id'],self.clue_id)
        with tempfile.TemporaryDirectory(prefix='CODEX-0917-files-') as directory:
            root=Path(directory);content=b'original clue document';target=root/'source.txt';target.write_bytes(content)
            async with self.sessions() as db:
                attachment=await db.get(FileAttachment,item['id']);attachment.path=str(target);await db.commit()
            with patch('app.core.storage.UPLOAD_ROOT',root):
                result=await self.client.get(f"{API}/attachments/{item['id']}/download")
                self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.content,content)
                preview=await self.client.get(f"{API}/attachments/{item['id']}/preview")
                self.assertEqual(preview.status_code,200,preview.text)
        self.assertFalse(root.exists())
