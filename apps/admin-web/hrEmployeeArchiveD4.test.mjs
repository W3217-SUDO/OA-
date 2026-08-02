import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'

const source = await readFile(new URL('./src/HrCenterPage.tsx', import.meta.url), 'utf8')

test('员工档案写入入口服从人事管理权限，查看和下载保持只读可用', () => {
  const archiveBranch = source.match(/if\(kind==='archive'\)\{([\s\S]*?)\n  \}/)
  assert.ok(archiveBranch, '应能定位员工档案分支')
  assert.match(archiveBranch[1], /canManage\?<Popconfirm title="确认删除该员工文档？"/)
  assert.match(archiveBranch[1], /\{canManage&&<Button type="primary" icon=\{<UploadOutlined\/>\}/)
  assert.match(archiveBranch[1], /onClick=\{\(\)=>void preview\(r\)\}>查看<\/Button>/)
  assert.match(archiveBranch[1], /onClick=\{\(\)=>void download\(r\)\}>下载<\/Button>/)
})

test('员工档案页接收与请假事项相同的人事管理权限', () => {
  assert.match(source, /\{key:'archive',label:'员工档案',children:<EmployeeSubrecords employeeId=\{employeeId\} kind="archive" canManage=\{actionAccess\.canProcessStatus\}\/>\}/)
})

test('员工档案保持旧站字段、空态、15条分页和可取消上传弹窗', () => {
  for (const title of ['序号', '上传人', '文件名称', '文档日期', '查看', '操作']) {
    assert.match(source, new RegExp(`title:'${title}'`))
  }
  assert.match(source, /pagination=\{\{pageSize:15,showSizeChanger:true,pageSizeOptions:\[10,15,20,50,100,200\]/)
  assert.match(source, /title="上传员工文档" okText="上传" cancelText="取消"/)
  assert.match(source, /onCancel=\{\(\)=>\{setUploadOpen\(false\);setUploadFile\(null\)\}\}/)
})
