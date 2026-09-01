import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = (await readFile(new URL('./src/InvestigationCenterPage.tsx', import.meta.url), 'utf8')).replace(/\s+/g, '').replace(/"/g, "'")

test('clue edit modal exposes every backend-editable investigation data field', () => {
  assert.match(source, /editTarget\?\.module==='clue'/)
  assert.match(source, /name='infringement_method'[\s\S]*name='platform'[\s\S]*name='product'[\s\S]*name='source'[\s\S]*name='address'/)
})

test('clue save sends the backend-editable investigation data fields', () => {
  assert.match(source, /data:\{region:v\.region\|\|''[\s\S]*address:v\.address\|\|''[\s\S]*infringement_method:v\.infringement_method\|\|''/)
  assert.match(source, /platform:v\.sales_channel\|\|''[\s\S]*sales_channel:v\.sales_channel\|\|''[\s\S]*product:v\.product\|\|''[\s\S]*source:v\.source\|\|''/)
})

test('clue edits from every review stage re-enter pending review', () => {
  assert.match(source, /constresubmit=editTarget\.module==='clue'/)
  assert.match(source, /status:'待审批'/)
  assert.match(source, /线索已修改并重新进入待审核/)
})

test('investigation task list does not offer a second parent-task creation entry', () => {
  assert.doesNotMatch(source, /investigation-task-published'\]:\['查询','刷新','新建调查任务'/)
  assert.doesNotMatch(source, /investigation-task-mine'\]:\['查询','刷新','新建调查任务'/)
})

test('parent investigation routes request server-side scoped views', () => {
  assert.match(source, /investigationListView=\(route:string\)=>/)
  assert.match(source, /route==='investigation-task-unassigned'[\s\S]*return'assigned'/)
  assert.match(source, /route==='investigation-task-mine'\)return'published'/)
  assert.match(source, /investigation_view:investigationListView\(initialTab\)/)
  assert.match(source, /scope:initialTab\.includes\('-my-'\)\|\|\(initialTab\.startsWith\('investigation-task-'\)&&!initialTab\.startsWith\('investigation-task-sub-'\)\)\?'mine':'all'/)
})

test('unassigned investigation tasks are scoped to the configured supervisor', () => {
  assert.match(source, /assignment-supervisor/)
  assert.match(source, /initialTab==='investigation-task-unassigned'[\s\S]*assignmentSupervisor[\s\S]*row\.owner===supervisor/)
})

test('clue create modal keeps legacy source, store and subject fields', () => {
  assert.match(source, /name='infringement_method'[\s\S]*name='store_url'[\s\S]*name='shop_id'[\s\S]*name='address'[\s\S]*name='investigated_at'[\s\S]*name='producer'[\s\S]*name='indictee'[\s\S]*name='investigation_assistant'/)
})

test('clue create uses server numbering and system person display labels', () => {
  assert.match(source, /serial_no:targetModule==='clue'\?'':values\.serial_no/)
  assert.match(source, /label='线索编号'name='serial_no'><Inputdisabled\/>/)
  assert.match(source, /label='调查员'name='owner'[^]*options=\{systemPersonOptions\}/)
  assert.match(source, /label='案源人'name='source_owner'[^]*options=\{systemPersonOptions\}/)
  assert.match(source, /value:item\.username\|\|item\.value,label:item\.label/)
})

test('clue create payload keeps legacy source, store and subject fields', () => {
  for (const key of ['infringement_method', 'store_url', 'shop_id', 'address', 'producer', 'indictee', 'investigation_assistant']) {
    assert.match(source, new RegExp(key + ':values\\.' + key + '\\|\\|\'\''))
  }
})

test('clue creation exposes draft, approval and attachment actions', () => {
  assert.match(source, /constcreate=async\(submitAfterCreate=false\)/)
  assert.match(source, /暂存线索/)
  assert.match(source, /提交审批/)
  assert.match(source, /record_id.*created\.id/)
  assert.match(source, /investigations\/clues\/\$\{created\.id\}\/submit/)
})

test('clue detail modal renders the legacy clue evidence and subject sections', () => {
  assert.match(source, /label:'侵权方式'[\s\S]*label:'店铺链接'[\s\S]*label:'生产商'[\s\S]*label:'主体信息'[\s\S]*label:'调查辅助'[\s\S]*label:'取证机构'[\s\S]*label:'证物状态'/)
})

test('customer review modal shows the previous auditor and opinion', () => {
  assert.match(source, /clueReviewing\?\.status==='待客户审核'[\s\S]*上一级审核员[\s\S]*上一级审核意见/)
})

test('clue lists retain customer manager presentation and review-stage edit actions', () => {
  assert.match(source, /title:'客户管理人'[\s\S]*customer_manager/)
  assert.match(source, /owner_display_name\|\|personDisplayName\(r\.owner\)/)
  assert.match(source, /source_owner_display_name\|\|personDisplayName\(r\.data\.source_owner\)/)
  assert.match(source, /customer_manager_display_name\|\|r\.data\.customer_manager/)
  assert.match(source, /clue-audit-pending[\s\S]*clue-audit-customer/)
  assert.match(source, /clue-my-pending[\s\S]*clue-my-customer[\s\S]*clue-my-collect[\s\S]*clue-my-collected/)
})

test('investigation keeps query controls above the table and selected-record actions below it', () => {
  assert.match(source, /constqueryActionLabels=actionLabels\.filter/)
  assert.match(source, /constbusinessActionLabels=actionLabels\.filter/)
  assert.match(source, /className='investigation-actionsinvestigation-actions-bottom'/)
})

test('collection uses enabled notary offices maintained in system parameters', () => {
  assert.match(source, /system\/parameters\/options/)
  assert.match(source, /category:'notary_office'/)
  assert.match(source, /notaryOfficeOptions\.map/)
})

test('case creation from collected clues keeps a missing source contract optional', () => {
  assert.match(source, /label='补充来源任务合同（可选）'/)
  assert.match(source, /message='来源调查任务未自动关联合同'/)
  assert.match(source, /本次可继续生成案件；案件将保留客户和线索关联/)
  assert.doesNotMatch(source, /来源调查任务未绑定合同，不能生成案件/)
})

test('case creation selects handling lawyers and assistants from active system people', () => {
  assert.match(source, /api\.get\('\/people\/options'\)/)
  assert.match(source, /label='经办律师'[^]*<SelectshowSearchoptionFilterProp='label'options=\{systemPersonOptions\}/)
  assert.match(source, /label='律师助理'[^]*<SelectallowClearshowSearchoptionFilterProp='label'options=\{systemPersonOptions\}/)
})

test('investigation supervisor creates a child directly under the contract investigation', () => {
  assert.match(source, /createSubtask&&hasParent\?parentTask\.id:undefined/)
  assert.match(source, /creatingSubtask&&!tasks\.some\(\(task\)=>!task\.parent_task_id\)/)
  assert.match(source, /creatingSubtask&&tasks\.some\(\(task\)=>!task\.parent_task_id\)/)
  assert.match(source, /constresetTaskForm=\(target:Row\)=>/)
  assert.match(source, /resetTaskForm\(taskContext\)/)
  assert.match(source, /title:'父调查任务'/)
  assert.match(source, /v\|\|row\.investigation_no\|\|taskTarget\?\.serial_no/)
  assert.match(source, /r\.data\.started_at\|\|r\.data\.authorized_from/)
  assert.match(source, /r\.data\.ended_at\|\|r\.data\.authorized_to\|\|r\.data\.deadline/)
})

test('investigation records load in parallel with auxiliary dropdown options', () => {
  assert.match(source, /awaitPromise\.all\(\[load\(initial\),loadInvestigationBootstrap\(\)/)
  assert.match(source, /api\.get\('\/people\/options'\)/)
  assert.match(source, /profile\.role!=='admin'&&Boolean\(profile\.username\)/)
  assert.match(source, /letinvestigationBootstrapPromise:/)
})

test('investigation people fields always render system display labels or the maintenance placeholder', () => {
  assert.match(source, /returnmatched\?\.label\|\|'姓名待维护'/)
  assert.match(source, /projectedPersonDisplayName\(row\.owner_display_name,row\.owner\)/)
  assert.match(source, /investigationDetail\.data\.source_owner_display_name/)
  assert.match(source, /investigationDetail\.data\.assigner_display_name/)
  assert.match(source, /clueReviewing\.data\.reviewer_display_name/)
  assert.match(source, /row\.uploader_display_name,row\.uploader/)
  assert.doesNotMatch(source, /\{title:'负责人',dataIndex:'owner',width:90\}/)
  assert.doesNotMatch(source, /children:linkedCase\.owner/)
})

test('investigation personnel inputs use system person selectors instead of username text inputs', () => {
  assert.match(source, /label='负责人\/调查员'name='owner'[^]*options=\{systemPersonOptions\}/)
  assert.match(source, /label='调查辅助员'name='investigation_assistant'[^]*options=\{systemPersonOptions\}/)
  assert.match(source, /label='调查员'name='investigator'[^]*options=\{systemPersonOptions\}/)
  assert.doesNotMatch(source, /label='调查员账号'/)
})
