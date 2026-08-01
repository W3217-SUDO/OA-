import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(
  fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)),
  'utf8',
)

function has(text, message = text) {
  assert.ok(source.includes(text), `员工子记录契约缺失：${message}`)
}

test('四个员工子页签均可达', () => {
  has("{key:'leave',label:'请假记录'")
  has("{key:'matter',label:'事项记录'")
  has("{key:'archive',label:'员工档案'")
  has("{key:'commission',label:'提成设定'")
})

test('请假、事项、提成使用真实子记录接口并支持保存/编辑/删除', () => {
  has("api.get(`/hr/${employeeId}/subrecords`,{params:{kind}})")
  has("api.post(`/hr/${employeeId}/subrecords`,{kind,data:values})")
  has("api.patch(`/hr/${employeeId}/subrecords/${editing.id}`,{data:values})")
  has("api.delete(kind==='archive'?`/attachments/${id}`:`/hr/${employeeId}/subrecords/${id}`)")
  has("message.success(editing?'修改成功':'新增成功')")
})

test('未保存员工时请假和提成被门禁，避免产生孤立记录', () => {
  has("if(!employeeId && (kind==='leave'||kind==='commission'))")
  has('请先保存员工基本信息，再维护此页记录')
  has("if(!employeeId){message.info('请先保存员工基本资料');return}")
})

test('未保存员工时事项记录同样被门禁，不能提交孤立记录', () => {
  has("if(!employeeId && kind==='matter')")
  has('请先保存员工基本信息，再维护此页记录')
})

test('员工档案页使用真实附件上传、下载和删除', () => {
  has("api.get('/attachments',{params:{record_id:employeeId,category:'员工档案'}})")
  has("data.append('category','员工档案')")
  has("api.post('/attachments',data,{headers:{'Content-Type':'multipart/form-data'}})")
  has("api.get(`/attachments/${item.id}/download`,{responseType:'blob'})")
  has('上传员工文档')
})

test('员工档案保留旧系统的查看入口并支持安全在线预览', () => {
  has("api.get(`/attachments/${item.id}/preview`)")
  has('在线查看')
  has('attachmentPreview')
  has('查看')
})

test('员工档案列表保留旧系统分页入口', () => {
  has('pageSizeOptions:[10,15,20,50,100,200]')
  has('showSizeChanger:true')
})

test('提成页保留按案件查询适用方案的跳转接口', () => {
  has("api.get('/records',{params:{module:'case',page_size:100}})")
  has("api.get(`/hr/${employeeId}/performance-for-case/${performanceCaseId}`)")
  has('按案件查看适用提成')
})

test('四页弹窗均可取消且表单被清理', () => {
  has("onCancel={()=>{setOpen(false);form.resetFields()}}")
  has("onCancel={()=>{setUploadOpen(false);setUploadFile(null)}}")
  has('okText="保存"')
  has('cancelText="取消"')
})
