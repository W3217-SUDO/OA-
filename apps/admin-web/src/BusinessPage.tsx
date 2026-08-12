import {useEffect, useMemo, useState} from 'react'
import {Alert, Button, Card, Descriptions, Divider, Drawer, Empty, Form, Input, message, Modal, Popconfirm, Select, Space, Table, Tag, Timeline} from 'antd'
import {DeleteOutlined, EditOutlined, EyeOutlined, PlusOutlined, ReloadOutlined, SearchOutlined} from '@ant-design/icons'
import {api} from './api'
import {rememberCaseDetailTarget} from './caseDetailNavigation'
import {rememberContractDetailTarget} from './contractDetailNavigation'
import {rememberCustomerDetailTarget} from './customerDetailNavigation'
import {rememberTaskDetailTarget} from './taskDetailNavigation'
import {rememberInvestigationDetailTarget} from './investigationDetailNavigation'

type RecordRow = {
  id:number; module:string; serial_no:string; title:string; customer:string; status:string;
  owner:string; owner_display_name?:string; department:string; description:string; data:Record<string,string|number>; updated_at:string
}

type ModuleConfig = {
  title:string; prefix:string; statuses:string[]; fields:{key:string;label:string;placeholder?:string}[]
}

type HistoryEvent = {id:number;action:string;from_status:string;to_status:string;operator:string;operator_display_name?:string;comment:string;created_at:string}
type HistoryData = {transitions:string[];items:HistoryEvent[]}

const personDisplayName=(value:unknown)=>String(value||'').trim()||'姓名待维护'

const configs:Record<string,ModuleConfig> = {
  customer:{title:'客户管理',prefix:'KH',statuses:['正常','跟进中','待共享','公海','已回收'],fields:[{key:'contact',label:'联系人'},{key:'phone',label:'联系电话'},{key:'level',label:'客户等级'}]},
  contract:{title:'合同中心',prefix:'HT',statuses:['草稿','审批中','已通过','履行中','已完成','已拒绝'],fields:[{key:'amount',label:'合同金额'},{key:'signed_at',label:'签订日期'},{key:'type',label:'合同类型'}]},
  case:{title:'案件中心',prefix:'AJ',statuses:['新案待分配','文书准备','一审立案受理','一审准备开庭','二审','执行','已归档'],fields:[{key:'court',label:'承办法院'},{key:'case_type',label:'案件类型'},{key:'opponent',label:'对方当事人'}]},
  task:{title:'事务中心',prefix:'RW',statuses:['待处理','处理中','已完成','已逾期','已撤回'],fields:[{key:'deadline',label:'截止日期'},{key:'priority',label:'优先级'},{key:'source',label:'任务来源'}]},
  clue:{title:'调查大厅',prefix:'XS',statuses:['草稿','待审批','调查中','待公证','已转案件','已驳回'],fields:[{key:'platform',label:'调查平台'},{key:'product',label:'侵权产品'},{key:'notary',label:'公证状态'}]},
  notary:{title:'公证管理',prefix:'GZ',statuses:['待审核','审核通过','审核驳回'],fields:[{key:'clue_no',label:'来源线索'},{key:'review_due_date',label:'审核期限'},{key:'case_no',label:'关联案件'}]},
  evidence:{title:'证据管理',prefix:'ZJ',statuses:['待整理','已整理','已入卷'],fields:[{key:'source',label:'材料来源'},{key:'clue_no',label:'关联线索'},{key:'case_no',label:'关联案件'}]},
  seal:{title:'用印中心',prefix:'YY',statuses:['草稿','待审批','待用印','已用印','已拒绝','已撤回'],fields:[{key:'seal_type',label:'印章类型'},{key:'copies',label:'用印份数'},{key:'purpose',label:'用印用途'}]},
  finance:{title:'财务中心',prefix:'FY',statuses:['草稿','待审批','已审批','已付款','已对账','已退回'],fields:[{key:'amount',label:'金额'},{key:'fee_type',label:'费用类型'},{key:'case_no',label:'关联案号'}]},
  document:{title:'收发文台',prefix:'SW',statuses:['待登记','待签收','已签收','已归档'],fields:[{key:'direction',label:'收发类型'},{key:'received_at',label:'收文日期'},{key:'case_no',label:'关联案号'}]},
  hr:{title:'人事中心',prefix:'RS',statuses:['在职','试用','离职','停用'],fields:[{key:'position',label:'职务'},{key:'phone',label:'联系电话'},{key:'joined_at',label:'入职日期'}]},
  warehouse:{title:'仓库管理',prefix:'CK',statuses:['在库','借出','归还中','报废'],fields:[{key:'category',label:'物品类别'},{key:'quantity',label:'数量'},{key:'location',label:'存放位置'}]},
  report:{title:'报表中心',prefix:'BB',statuses:['生成中','已生成','已发布'],fields:[{key:'report_type',label:'报表类型'},{key:'period',label:'统计期间'},{key:'format',label:'文件格式'}]},
  system:{title:'系统中心',prefix:'XT',statuses:['启用','停用'],fields:[{key:'type',label:'配置类型'},{key:'value',label:'配置值'},{key:'scope',label:'生效范围'}]},
}

const statusColors:Record<string,string> = {'正常':'green','履行中':'green','已完成':'green','已通过':'green','已签收':'green','已归档':'green','已用印':'green','已付款':'green','已审批':'green','待审批':'orange','审批中':'orange','待处理':'blue','处理中':'blue','调查中':'blue','草稿':'default','已拒绝':'red','已驳回':'red','已逾期':'red','已退回':'red'}

function nextSerial(prefix:string){
  const d=new Date(); const pad=(v:number,n=2)=>String(v).padStart(n,'0')
  return `${prefix}${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
}

export default function BusinessPage({module,title,openCreate=false,defaultStatus='',onNavigate}:{module:string;title?:string;openCreate?:boolean;defaultStatus?:string;onNavigate?: (route:string)=>void}){
  const config=configs[module]||configs.system
  const [rows,setRows]=useState<RecordRow[]>([])
  const [total,setTotal]=useState(0)
  const [loading,setLoading]=useState(false)
  const [page,setPage]=useState(1)
  const [keyword,setKeyword]=useState('')
  const [recordStatus,setRecordStatus]=useState(defaultStatus)
  const [modalOpen,setModalOpen]=useState(false)
  const [editing,setEditing]=useState<RecordRow|null>(null)
  const [viewing,setViewing]=useState<RecordRow|null>(null)
  const [history,setHistory]=useState<HistoryData>({transitions:[],items:[]})
  const [transitionOpen,setTransitionOpen]=useState(false)
  const [transitionTarget,setTransitionTarget]=useState('')
  const [transitionComment,setTransitionComment]=useState('')
  const [form]=Form.useForm()
  const openBusinessTarget=(targetModule:string,serialNo?:unknown,id?:number,titleText?:string)=>{
    const serial=String(serialNo||'').trim()
    if(targetModule==='case'){rememberCaseDetailTarget({id,serial_no:serial});onNavigate?.('case-company');return}
    if(targetModule==='contract'){rememberContractDetailTarget({id,serial_no:serial});onNavigate?.('contract-company');return}
    if(targetModule==='customer'){rememberCustomerDetailTarget({id,serial_no:serial,title:titleText});onNavigate?.('customer-company');return}
    if(targetModule==='task'){rememberTaskDetailTarget({id,serial_no:serial});onNavigate?.('task-company-accepted');return}
    if(['clue','notary','evidence'].includes(targetModule)){rememberInvestigationDetailTarget({id,serial_no:serial,module:targetModule});onNavigate?.(targetModule);return}
    if(viewing) void openDetails(viewing)
  }
  const renderLinkedField=(field:{key:string;label:string},value:unknown)=>{
    const text=String(value??'')
    if(!text||text==='-')return '-'
    if(field.key==='case_no'||field.label.includes('案'))return <Button type="link" onClick={()=>openBusinessTarget('case',text)}>{text}</Button>
    if(field.key==='contract_no'||field.label.includes('合同'))return <Button type="link" onClick={()=>openBusinessTarget('contract',text)}>{text}</Button>
    if(field.key==='clue_no'||field.label.includes('线索'))return <Button type="link" onClick={()=>openBusinessTarget('clue',text)}>{text}</Button>
    return text
  }

  const load=async(nextPage=page,nextKeyword=keyword,nextRecordStatus=recordStatus)=>{setLoading(true);try{const {data}=await api.get('/records',{params:{module,keyword:nextKeyword,record_status:nextRecordStatus,page:nextPage,page_size:20}});setRows(data.items);setTotal(data.total)}catch{message.error('业务数据加载失败')}finally{setLoading(false)}}
  useEffect(()=>{setPage(1);load(1)},[module])
  useEffect(()=>{if(openCreate)startCreate()},[module,openCreate])

  const startCreate=()=>{if(module==='task'){message.warning('请使用事务中心专用入口');return}setEditing(null);form.resetFields();form.setFieldsValue({serial_no:nextSerial(config.prefix),status:config.statuses[0],owner:'管理者',department:'上海分所'});setModalOpen(true)}
  const startEdit=(row:RecordRow)=>{setEditing(row);form.setFieldsValue({...row,...row.data});setModalOpen(true)}
  const openDetails=async(row:RecordRow)=>{setViewing(row);setHistory({transitions:[],items:[]});try{const {data}=await api.get(`/records/${row.id}/history`);setHistory(data)}catch{message.error('流程记录加载失败')}}
  const save=async()=>{if(module==='task'){message.warning('请使用事务中心专用入口');return}const values=await form.validateFields();const data=Object.fromEntries(config.fields.map(f=>[f.key,values[f.key]??'']));const payload={module,serial_no:values.serial_no,title:values.title,customer:values.customer||'',status:values.status,owner:values.owner,department:values.department,description:values.description||'',data};try{if(editing)await api.patch(`/records/${editing.id}`,payload);else await api.post('/records',payload);message.success(editing?'保存成功':'新增成功');setModalOpen(false);load()}catch(error:any){message.error(error?.response?.data?.detail||'保存失败')}}
  const remove=async(id:number)=>{if(module==='task'){message.warning('请使用事务中心专用入口');return}try{await api.delete(`/records/${id}`);message.success('已删除');load()}catch{message.error('删除失败')}}
  const startTransition=(target:string)=>{setTransitionTarget(target);setTransitionComment('');setTransitionOpen(true)}
  const submitTransition=async()=>{if(!viewing)return;if(module==='task'){message.warning('禁止使用通用记录接口流转任务');return}try{const {data}=await api.post(`/records/${viewing.id}/transition`,{to_status:transitionTarget,comment:transitionComment});message.success(`已流转至“${transitionTarget}”`);setViewing(data);setTransitionOpen(false);const result=await api.get(`/records/${viewing.id}/history`);setHistory(result.data);load()}catch(error:any){message.error(error?.response?.data?.detail||'流程操作失败')}}

  const columns=useMemo(()=>[
    {title:'业务编号',dataIndex:'serial_no',width:145,fixed:'left' as const,render:(value:string,row:RecordRow)=><a onClick={()=>openDetails(row)}>{value}</a>},
    {title:'标题/事项',dataIndex:'title',width:220,ellipsis:true},
    {title:'客户/主体',dataIndex:'customer',width:190,ellipsis:true,render:(value:string,row:RecordRow)=>value?<Button type="link" onClick={()=>openBusinessTarget('customer',row.data?.customer_no,undefined,value)}>{value}</Button>:'-'},
    {title:'状态',dataIndex:'status',width:100,render:(value:string)=><Tag color={statusColors[value]||'blue'}>{value}</Tag>},
    {title:'负责人',dataIndex:'owner_display_name',width:90,render:(value:string)=>personDisplayName(value)},
    {title:'部门',dataIndex:'department',width:105},
    ...config.fields.slice(0,2).map(field=>({title:field.label,key:field.key,width:130,ellipsis:true,render:(_:unknown,row:RecordRow)=>renderLinkedField(field,row.data?.[field.key]??'-')})),
    {title:'更新时间',dataIndex:'updated_at',width:160,render:(v:string)=>v?new Date(v).toLocaleString('zh-CN'):'-'},
    {title:'操作',key:'actions',fixed:'right' as const,width:150,render:(_:unknown,row:RecordRow)=><Space><Button type="link" size="small" icon={<EyeOutlined/>} onClick={()=>openDetails(row)}>查看</Button><Button type="link" size="small" icon={<EditOutlined/>} onClick={()=>startEdit(row)}>编辑</Button><Popconfirm title="确认删除这条记录？" onConfirm={()=>remove(row.id)}><Button danger type="link" size="small" icon={<DeleteOutlined/>}/></Popconfirm></Space>},
  ],[module, rows, onNavigate])

  if (module === "task") {
    return (
      <Card className="panel business-panel" title={title || config.title}>
        <Alert
          type="info"
          showIcon
          message="事务中心请使用专用入口"
          description="禁止使用通用记录接口新建或流转任务；请从我的任务、我接受的任务或未读消息进入事务中心操作。"
        />
        <Space wrap style={{ marginTop: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => onNavigate?.("task-my-created")}>我的任务</Button>
          <Button icon={<ReloadOutlined />} onClick={() => onNavigate?.("task-my-accepted")}>我接受的任务</Button>
          <Button icon={<EyeOutlined />} onClick={() => onNavigate?.("task-my-unread")}>未读消息</Button>
        </Space>
      </Card>
    );
  }

  return <>
    <Card className="panel business-panel" title={title||config.title} extra={<Space><Button icon={<ReloadOutlined/>} onClick={()=>load()}>刷新</Button><Button type="primary" icon={<PlusOutlined/>} onClick={startCreate}>新建</Button></Space>}>
      <div className="filter-bar"><Input allowClear value={keyword} onChange={e=>setKeyword(e.target.value)} onPressEnter={()=>{setPage(1);load(1)}} placeholder="编号、标题、客户或负责人" prefix={<SearchOutlined/>}/><Select allowClear value={recordStatus||undefined} onChange={v=>setRecordStatus(v||'')} placeholder="全部状态" options={config.statuses.map(v=>({label:v,value:v}))}/><Button type="primary" onClick={()=>{setPage(1);load(1)}}>查询</Button><Button onClick={()=>{setKeyword('');setRecordStatus('');setPage(1);void load(1,'','')}}>重置</Button></div>
      <Table rowKey="id" loading={loading} columns={columns} dataSource={rows} size="small" scroll={{x:1250}} pagination={{current:page,total,pageSize:20,showTotal:n=>`共 ${n} 条`,onChange:p=>{setPage(p);load(p)}}}/>
    </Card>
    <Modal width={760} open={modalOpen} title={`${editing?'编辑':'新建'}${title||config.title}`} okText="保存" cancelText="取消" onOk={save} onCancel={()=>setModalOpen(false)} destroyOnHidden>
      <Form form={form} layout="vertical"><div className="form-grid"><Form.Item label="业务编号" name="serial_no" rules={[{required:true}]}><Input disabled={Boolean(editing)}/></Form.Item><Form.Item label="流程状态" name="status" rules={[{required:true}]}><Select options={config.statuses.map(v=>({label:v,value:v}))}/></Form.Item><Form.Item className="span-2" label="标题/事项" name="title" rules={[{required:true,message:'请输入标题'}]}><Input/></Form.Item><Form.Item label="客户/主体" name="customer"><Input/></Form.Item><Form.Item label="负责人" name="owner" rules={[{required:true}]}><Input/></Form.Item><Form.Item label="所属部门" name="department"><Input/></Form.Item>{config.fields.map(field=><Form.Item key={field.key} label={field.label} name={field.key}><Input placeholder={field.placeholder}/></Form.Item>)}<Form.Item className="span-2" label="备注说明" name="description"><Input.TextArea rows={3}/></Form.Item></div></Form>
    </Modal>
    <Drawer size={620} open={Boolean(viewing)} title={`${title||config.title}详情`} onClose={()=>setViewing(null)} extra={viewing&&<Button type="primary" onClick={()=>{startEdit(viewing);setViewing(null)}}>编辑</Button>}>
      {viewing&&<><Descriptions bordered column={2} size="small"><Descriptions.Item label="业务编号">{viewing.serial_no}</Descriptions.Item><Descriptions.Item label="状态"><Tag color={statusColors[viewing.status]||'blue'}>{viewing.status}</Tag></Descriptions.Item><Descriptions.Item label="标题" span={2}>{viewing.title}</Descriptions.Item><Descriptions.Item label="客户/主体" span={2}>{viewing.customer?<Button type="link" onClick={()=>openBusinessTarget('customer',viewing.data?.customer_no,undefined,viewing.customer)}>{viewing.customer}</Button>:'-'}</Descriptions.Item><Descriptions.Item label="负责人">{personDisplayName(viewing.owner_display_name)}</Descriptions.Item><Descriptions.Item label="部门">{viewing.department}</Descriptions.Item>{config.fields.map(f=><Descriptions.Item key={f.key} label={f.label}>{renderLinkedField(f,viewing.data?.[f.key]??'-')}</Descriptions.Item>)}<Descriptions.Item label="备注" span={2}>{viewing.description||'-'}</Descriptions.Item></Descriptions><Divider titlePlacement="start">流程操作</Divider>{history.transitions.length?<Space wrap>{history.transitions.map(target=><Button key={target} type={['已拒绝','已驳回','已退回','已撤回'].includes(target)?'default':'primary'} danger={['已拒绝','已驳回','已退回'].includes(target)} onClick={()=>startTransition(target)}>{target}</Button>)}</Space>:<span className="workflow-finished">当前状态暂无后续操作</span>}<Divider titlePlacement="start">审批与操作记录</Divider>{history.items.length?<Timeline items={history.items.map(event=>({color:event.action.includes('驳回')?'red':event.action==='创建'?'blue':'green',children:<div className="history-item"><b>{event.action}</b>{event.from_status&&event.from_status!==event.to_status&&<span>{event.from_status} → {event.to_status}</span>}<small>{personDisplayName(event.operator_display_name)} · {new Date(event.created_at).toLocaleString('zh-CN')}</small>{event.comment&&<p>{event.comment}</p>}</div>}))}/>:<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无操作记录"/>}</>}
    </Drawer>
    <Modal open={transitionOpen} title={`流程操作：${transitionTarget}`} okText="确认提交" cancelText="取消" onOk={submitTransition} onCancel={()=>setTransitionOpen(false)}><p>当前状态：<Tag>{viewing?.status}</Tag> → 目标状态：<Tag color="green">{transitionTarget}</Tag></p><Input.TextArea rows={4} value={transitionComment} onChange={e=>setTransitionComment(e.target.value)} placeholder="填写审批意见、办理说明或驳回原因"/></Modal>
  </>
}

export function moduleFromMenuKey(key:string){
  if(key.startsWith('customer'))return 'customer'
  if(key.startsWith('contract'))return 'contract'
  if(key.startsWith('case'))return 'case'
  if(key.startsWith('task'))return 'task'
  if(key==='investigation'||key==='clue')return 'clue'
  if(key==='notary')return 'notary'
  if(key==='evidence')return 'evidence'
  if(key.startsWith('seal'))return 'seal'
  if(key==='finance')return 'finance'
  if(key==='documents')return 'document'
  if(key==='reports')return 'report'
  return key
}
