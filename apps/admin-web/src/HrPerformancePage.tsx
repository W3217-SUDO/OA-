import {useEffect, useRef, useState} from 'react'
import {Alert, Button, Card, DatePicker, Descriptions, Form, Input, InputNumber, message, Modal, Popconfirm, Select, Space, Table} from 'antd'
import type {TableColumnsType} from 'antd'
import {DownloadOutlined, PlusOutlined, ReloadOutlined} from '@ant-design/icons'
import dayjs from 'dayjs'
import type {Dayjs} from 'dayjs'
import {api} from './api'
import {formatRequiredDate} from './formSafety'
import {rememberBusinessRecordDetailTarget} from './businessRecordDetailNavigation'
import './hr-center.css'

type Performance = {id:number;employee_id:number;employee_name:string;employee_no:string;department:string;data:Record<string,any>}
type Option = {value:number;label:string}
type Filters = {employee?:string;department?:string;start_date?:string;end_date?:string}
const amounts = [['base_salary','基本工资'],['hearing_rate','开庭比例'],['hearing_fixed','开庭固定'],['document_rate','文书比例'],['document_fixed','文书固定'],['source_rate','案源比例'],['source_fixed','案源固定'],['investigation_rate','调查比例'],['investigation_fixed','调查固定'],['quality_rate','品管比例'],['quality_fixed','品管固定']]
const defaults = {base_salary:0,hearing_rate:0.10,hearing_fixed:0,document_rate:0.05,document_fixed:0,source_rate:0.05,source_fixed:0,investigation_rate:0.05,investigation_fixed:0,quality_rate:0.02,quality_fixed:0}
const errorText = (error:any, fallback:string) => typeof error?.response?.data?.detail==='string'?error.response.data.detail:fallback

export default function HrPerformancePage({onNavigate}:{onNavigate:(route:string)=>void}) {
  const [rows,setRows]=useState<Performance[]>([]),[total,setTotal]=useState(0),[loading,setLoading]=useState(false)
  const [page,setPage]=useState(1),[pageSize,setPageSize]=useState(15),[filters,setFilters]=useState<Filters>({})
  const [employee,setEmployee]=useState(''),[department,setDepartment]=useState<string>(),[dates,setDates]=useState<[Dayjs|null,Dayjs|null]|null>(null)
  const [departments,setDepartments]=useState<{value:string;label:string}[]>([]),[employees,setEmployees]=useState<Option[]>([]),[employeeLoading,setEmployeeLoading]=useState(false)
  const [canManage,setCanManage]=useState(false),[editing,setEditing]=useState<Performance|null>(null),[open,setOpen]=useState(false),[viewing,setViewing]=useState<Performance|null>(null)
  const [saving,setSaving]=useState(false),[exporting,setExporting]=useState(false),[deleting,setDeleting]=useState<number|null>(null),[failure,setFailure]=useState(''),[form]=Form.useForm()
  const listRequest=useRef(0),employeeRequest=useRef(0)
  const load=async()=>{
    const request=++listRequest.current
    setLoading(true);setFailure('')
    try {const {data}=await api.get('/hr/performance',{params:{...filters,page,page_size:pageSize}});if(request!==listRequest.current)return;setRows(data.items);setTotal(data.total)}
    catch(error){if(request===listRequest.current){setRows([]);setTotal(0);setFailure(errorText(error,'绩效列表加载失败，请重试'))}}
    finally{if(request===listRequest.current)setLoading(false)}
  }
  useEffect(()=>{void load();return()=>{listRequest.current++}},[filters,page,pageSize])
  useEffect(()=>{let active=true;void Promise.allSettled([api.get('/auth/me'),api.get('/hr/departments')]).then(([profile,ds])=>{
    if(!active)return
    if(profile.status==='fulfilled')setCanManage(['admin','manager'].includes(profile.value.data.role))
    else message.error('绩效操作权限加载失败')
    if(ds.status==='fulfilled')setDepartments(ds.value.data.items.map((item:{name:string})=>({value:item.name,label:item.name})))
    else message.error('部门筛选项加载失败')
  });return()=>{active=false}},[])
  const searchEmployees=async(name='')=>{
    const request=++employeeRequest.current;setEmployeeLoading(true)
    try{const {data}=await api.get('/hr/employees',{params:{name,page:1,page_size:100}});if(request===employeeRequest.current)setEmployees(data.items.filter((item:any)=>item.id>0).map((item:any)=>({value:item.id,label:`${item.person_display_name||item.title||'姓名待维护'} · ${item.serial_no||''} · ${item.department||'未分配部门'}`})))}
    catch(error){if(request===employeeRequest.current){setEmployees([]);message.error(errorText(error,'员工候选加载失败'))}}
    finally{if(request===employeeRequest.current)setEmployeeLoading(false)}
  }
  const showEditor=async(row?:Performance)=>{
    try{
      const record:Performance|null=row?(await api.get(`/hr/performance/${row.id}`)).data:null
      form.resetFields();setEditing(record)
      form.setFieldsValue({...defaults,...record?.data,employee_id:record?.employee_id,start_date:record?.data.start_date?dayjs(record.data.start_date):dayjs(),end_date:record?record.data.end_date?dayjs(record.data.end_date):null:dayjs().add(1,'year')})
      if(record)setEmployees([{value:record.employee_id,label:`${record.employee_name} · ${record.employee_no}`}]);else void searchEmployees()
      setOpen(true)
    }catch(error){message.error(errorText(error,'绩效设置加载失败'))}
  }
  const save=async()=>{
    let values:Record<string,any>;try{values=await form.validateFields()}catch{return}
    setSaving(true)
    const {employee_id,...fields}=values
    const data={...(editing?.data||{}),...fields,start_date:formatRequiredDate(values.start_date,'开始日期'),end_date:values.end_date?.format('YYYY-MM-DD')||''}
    try{if(editing)await api.patch(`/hr/performance/${editing.id}`,{data});else await api.post('/hr/performance',{employee_id,data});message.success('绩效方案已保存');setOpen(false);form.resetFields();await load()}
    catch(error){message.error(errorText(error,'绩效方案保存失败'))}finally{setSaving(false)}
  }
  const remove=async(row:Performance)=>{setDeleting(row.id);try{await api.delete(`/hr/performance/${row.id}`);message.success('绩效记录已删除');if(rows.length===1&&page>1)setPage(page-1);else await load()}catch(error){message.error(errorText(error,'绩效记录删除失败'))}finally{setDeleting(null)}}
  const showDetails=async(row:Performance)=>{try{setViewing((await api.get(`/hr/performance/${row.id}`)).data)}catch(error){message.error(errorText(error,'绩效详情加载失败'))}}
  const openEmployee=(row:Performance)=>{if(rememberBusinessRecordDetailTarget({module:'hr',id:row.employee_id}))onNavigate('hr-all')}
  const exportCsv=async()=>{
    setExporting(true)
    try{const {data}=await api.get('/hr/performance/export',{params:filters,responseType:'blob'});const url=URL.createObjectURL(data);const link=document.createElement('a');link.href=url;link.download=`员工绩效_${dayjs().format('YYYYMMDD')}.csv`;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
    catch(error:any){let detail='绩效导出失败';if(error?.response?.data instanceof Blob){try{const body=JSON.parse(await error.response.data.text());if(typeof body.detail==='string')detail=body.detail}catch{/* Keep the useful fallback for non-JSON failures. */}}message.error(errorText(error,detail))}
    finally{setExporting(false)}
  }
  const columns:TableColumnsType<Performance>=[
    {title:'员工',key:'employee',width:140,render:(_,row)=><Button type="link" style={{padding:0}} onClick={()=>openEmployee(row)}>{row.employee_name||'姓名待维护'}</Button>},
    {title:'员工编号',dataIndex:'employee_no',width:130},{title:'部门',dataIndex:'department',width:140},
    {title:'方案名称',dataIndex:['data','scheme_name'],width:180,render:value=>value||'提成方案'},
    {title:'开始日期',dataIndex:['data','start_date'],width:120},{title:'结束日期',dataIndex:['data','end_date'],width:120,render:value=>value||'长期'},
    {title:'基本工资',dataIndex:['data','base_salary'],width:110,render:value=>value??0},
    {title:'操作',key:'actions',width:220,render:(_,row)=><Space size={4}><Button size="small" type="link" onClick={()=>void showDetails(row)}>查看</Button>{canManage&&<><Button size="small" type="link" onClick={()=>void showEditor(row)}>绩效设置 / 编辑</Button><Popconfirm title="确定删除此绩效记录？" description="删除后将不再用于该员工的提成方案匹配。" onConfirm={()=>remove(row)} okText="删除" cancelText="取消"><Button size="small" type="link" danger loading={deleting===row.id}>删除</Button></Popconfirm></>}</Space>},
  ]
  return <Card className="panel hr-panel" title="绩效管理">
    <div className="hr-query">
      <label><span>员工</span><Input aria-label="员工筛选" placeholder="姓名或员工编号" value={employee} onChange={event=>setEmployee(event.target.value)} allowClear/></label>
      <label><span>部门</span><Select aria-label="部门筛选" placeholder="全部部门" value={department} onChange={setDepartment} options={departments} showSearch allowClear optionFilterProp="label"/></label>
      <label><span>有效期</span><DatePicker.RangePicker aria-label="绩效有效期筛选" value={dates} onChange={setDates} allowEmpty={[true,true]} style={{minWidth:0,width:'100%'}}/></label>
      <Space><Button type="primary" onClick={()=>{setPage(1);setFilters({employee:employee.trim()||undefined,department,start_date:dates?.[0]?.format('YYYY-MM-DD'),end_date:dates?.[1]?.format('YYYY-MM-DD')})}}>查询</Button><Button onClick={()=>{setEmployee('');setDepartment(undefined);setDates(null);setPage(1);setFilters({})}}>重置</Button></Space>
    </div>
    <div className="subrecord-toolbar"><Space wrap>{canManage&&<Button type="primary" icon={<PlusOutlined/>} onClick={()=>void showEditor()}>新增绩效</Button>}<Button icon={<DownloadOutlined/>} loading={exporting} onClick={()=>void exportCsv()}>导出 CSV</Button><Button icon={<ReloadOutlined/>} loading={loading} onClick={()=>void load()}>刷新</Button></Space></div>
    {failure&&<Alert type="error" showIcon message={failure} style={{marginBottom:12}}/>}
    <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={rows} scroll={{x:1160}} pagination={{current:page,pageSize,total,showSizeChanger:true,showTotal:count=>`共 ${count} 条`,onChange:(next,size)=>{setPage(size!==pageSize?1:next);setPageSize(size)}}}/>
    <Modal open={open} title={editing?'绩效设置 / 编辑':'新增绩效 / 方案设置'} width={740} okText="保存" cancelText="取消" confirmLoading={saving} onOk={()=>void save()} onCancel={()=>{if(!saving){setOpen(false);form.resetFields()}}} destroyOnHidden maskClosable={!saving} closable={!saving}>
      <Form form={form} layout="vertical">
        <Form.Item name="employee_id" label="员工" rules={[{required:true,message:'请选择员工'}]}><Select showSearch filterOption={false} disabled={Boolean(editing)} loading={employeeLoading} options={employees} onSearch={value=>void searchEmployees(value)} placeholder="输入员工姓名搜索"/></Form.Item>
        <Form.Item name="scheme_name" label="方案名称" rules={[{max:128,message:'方案名称最多 128 个字符'}]}><Input maxLength={128} placeholder="例如：年度提成方案"/></Form.Item>
        <div className="commission-form-grid">
          <Form.Item name="start_date" label="开始日期" rules={[{required:true,message:'请选择开始日期'}]}><DatePicker style={{width:'100%'}}/></Form.Item>
          <Form.Item name="end_date" label="结束日期" dependencies={['start_date']} rules={[{required:true,message:'请选择结束日期'},({getFieldValue})=>({validator:(_,value)=>!value||!getFieldValue('start_date')||!value.isBefore(getFieldValue('start_date'),'day')?Promise.resolve():Promise.reject(new Error('结束日期不能早于开始日期'))})]}><DatePicker style={{width:'100%'}}/></Form.Item>
          {amounts.map(([key,label])=><Form.Item key={key} name={key} label={`${label}${key.endsWith('_rate')?'（比例值，同员工提成设定）':''}`} rules={[{required:true,message:`请填写${label}`}]}><InputNumber min={0} precision={key.endsWith('_rate')?4:2} step={key.endsWith('_rate')?0.01:1} style={{width:'100%'}}/></Form.Item>)}
        </div>
        <Form.Item name="remark" label="备注" rules={[{max:2000,message:'备注最多 2000 个字符'}]}><Input.TextArea rows={3} maxLength={2000} showCount/></Form.Item>
      </Form>
    </Modal>
    <Modal open={Boolean(viewing)} title="绩效查看" width={740} footer={<Button onClick={()=>setViewing(null)}>关闭</Button>} onCancel={()=>setViewing(null)} destroyOnHidden>
      {viewing&&<Descriptions bordered size="small" column={2} items={[
        {key:'employee',label:'员工',children:<Button type="link" style={{padding:0}} onClick={()=>openEmployee(viewing)}>{viewing.employee_name||'姓名待维护'}</Button>},
        {key:'employee_no',label:'员工编号',children:viewing.employee_no||'—'},{key:'department',label:'部门',children:viewing.department||'—'},
        {key:'name',label:'方案名称',children:viewing.data.scheme_name||'提成方案'},
        {key:'start_date',label:'开始日期',children:viewing.data.start_date||'—'},{key:'end_date',label:'结束日期',children:viewing.data.end_date||'长期'},
        ...amounts.map(([key,label])=>({key,label,children:viewing.data[key]??0})),
        {key:'remark',label:'备注',span:2,children:viewing.data.remark||'—'},
      ]}/>}
    </Modal>
  </Card>
}
