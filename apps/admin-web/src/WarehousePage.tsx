import {useEffect, useMemo, useState, type Key} from 'react'
import {Button, Card, DatePicker, Descriptions, Dropdown, Empty, Form, Input, message, Modal, Select, Space, Table, Tag, Timeline, Tree} from 'antd'
import type {MenuProps, TableColumnsType, TreeDataNode} from 'antd'
import {EllipsisOutlined} from '@ant-design/icons'
import dayjs, {type Dayjs} from 'dayjs'
import {api} from './api'
import {rememberCaseDetailTarget} from './caseDetailNavigation'
import {rememberCustomerDetailTarget} from './customerDetailNavigation'
import {formatRequiredDate} from './formSafety'
import {rememberInvestigationDetailTarget} from './investigationDetailNavigation'
import {consumeBusinessRecordDetailTarget} from './businessRecordDetailNavigation'
import {resolveDetailRelation} from './detailRelationResolver'
import './warehouse.css'

type EvidenceData=Record<string, string|number>
type Item={id:number;serial_no:string;title:string;customer:string;status:string;owner:string;department:string;description:string;data:EvidenceData}
type WorkflowItem={id:number;action:string;from_status:string;to_status:string;operator:string;comment:string;created_at:string}
type ActionKind='check-in'|'check-out'|'recheck-in'|'destroy'

const warehouses=['上海一仓','上海二仓','嘉兴一仓','无锡一仓','合肥一仓','武汉一仓','重庆一仓','时间戳']
const evidenceStatuses=['未入库','已入库','已出库','已重新入库','已销毁']
const statusColor:Record<string,string>={未入库:'default',已入库:'green',已出库:'orange',已重新入库:'cyan',已销毁:'red'}
const statusOf=(row:Item)=>String(row.data?.evidence_status||({在库:'已入库',借出:'已出库',归还中:'已出库',报废:'已销毁'} as Record<string,string>)[row.status]||'未入库')

export default function WarehousePage({onNavigate}:{onNavigate?: (route:string)=>void}){
  const [allRows,setAllRows]=useState<Item[]>([])
  const [loading,setLoading]=useState(false)
  const [warehouse,setWarehouse]=useState('')
  const [location,setLocation]=useState('')
  const [rightsHolder,setRightsHolder]=useState('')
  const [status,setStatus]=useState('')
  const [caseNo,setCaseNo]=useState('')
  const [shop,setShop]=useState('')
  const [investigator,setInvestigator]=useState('')
  const [notaryNo,setNotaryNo]=useState('')
  const [dates,setDates]=useState<[Dayjs|null,Dayjs|null]|null>(null)
  const [editorOpen,setEditorOpen]=useState(false)
  const [editing,setEditing]=useState<Item|null>(null)
  const [action,setAction]=useState<{kind:ActionKind;row:Item}|null>(null)
  const [historyRow,setHistoryRow]=useState<Item|null>(null)
  const [history,setHistory]=useState<WorkflowItem[]>([])
  const [saving,setSaving]=useState(false)
  const [form]=Form.useForm()
  const [actionForm]=Form.useForm()

  const load=async()=>{setLoading(true);try{const {data}=await api.get('/records',{params:{module:'warehouse',page_size:100}});setAllRows(data.items)}catch{message.error('仓库数据加载失败')}finally{setLoading(false)}}
  useEffect(()=>{void load()},[])
  const rows=useMemo(()=>allRows.filter(row=>{
    const d=row.data||{}
    const contains=(value:unknown,term:string)=>!term||String(value||'').includes(term)
    const evidenceDate=String(d.evidence_date||d.collected_at||'')
    return (!warehouse||String(d.warehouse||row.department)===warehouse)&&contains(d.location,location)&&contains(d.rights_holder||row.customer,rightsHolder)&&(!status||statusOf(row)===status)&&contains(d.case_no,caseNo)&&contains(d.shop_name||row.title,shop)&&contains(d.investigator||row.owner,investigator)&&contains(d.notary_no,notaryNo)&&(!dates?.[0]||evidenceDate>=dates[0].format('YYYY-MM-DD'))&&(!dates?.[1]||evidenceDate<=dates[1].format('YYYY-MM-DD'))
  }),[allRows,warehouse,location,rightsHolder,status,caseNo,shop,investigator,notaryNo,dates])
  const warehouseOptions=useMemo(()=>[...new Set([...warehouses,...allRows.map(row=>String(row.data?.warehouse||row.department||'').trim()).filter(Boolean)])].sort(),[allRows])
  const storageTreeData=useMemo<TreeDataNode[]>(()=>{
    const grouped=new Map<string,Map<string,number>>()
    allRows.forEach(row=>{
      const data=row.data||{}
      const warehouseName=String(data.warehouse||row.department||'未设置仓库').trim()||'未设置仓库'
      const locationName=String(data.location||'未设置库位').trim()||'未设置库位'
      const locations=grouped.get(warehouseName)||new Map<string,number>()
      locations.set(locationName,(locations.get(locationName)||0)+1)
      grouped.set(warehouseName,locations)
    })
    return [...grouped.entries()].sort(([left],[right])=>left.localeCompare(right,'zh-CN')).map(([warehouseName,locations])=>{
      const total=[...locations.values()].reduce((sum,count)=>sum+count,0)
      return {key:`warehouse:${warehouseName}`,title:`${warehouseName}（${total}）`,children:[...locations.entries()].sort(([left],[right])=>left.localeCompare(right,'zh-CN')).map(([locationName,count])=>({key:`location:${warehouseName}\u0000${locationName}`,title:`${locationName}（${count}）`}))}
    })
  },[allRows])

  const openEditor=(row?:Item)=>{
    setEditing(row||null)
    form.resetFields()
    if(row){const d=row.data||{};form.setFieldsValue({serial_no:row.serial_no,warehouse:d.warehouse||'',location:d.location||'',notary_no:d.notary_no||'',case_no:d.case_no||'',shop_name:d.shop_name||row.title,investigator:d.investigator||row.owner,notary_office:d.notary_office||'',rights_holder:d.rights_holder||'',evidence_date:d.evidence_date?dayjs(String(d.evidence_date)):null,description:row.description||''})}
    setEditorOpen(true)
  }
  const saveEvidence=async()=>{try{const values=await form.validateFields();setSaving(true);const payload={...values,evidence_date:formatRequiredDate(values.evidence_date,'取证日期')};if(editing)await api.patch(`/warehouse/evidence/${editing.id}`,payload);else await api.post('/warehouse/evidence',payload);message.success(editing?'证物资料已保存':'证物已登记');setEditorOpen(false);await load()}catch(error:any){if(error?.errorFields)return;message.error(error?.response?.data?.detail||error?.message||'证物保存失败')}finally{setSaving(false)}}

  const openAction=(kind:ActionKind,row:Item)=>{setAction({kind,row});actionForm.resetFields();const d=row.data||{};if(kind==='check-in'||kind==='recheck-in')actionForm.setFieldsValue({warehouse:d.warehouse||'',location:d.location||'',condition:'完好'});setTimeout(()=>actionForm.getFieldInstance(kind==='destroy'?'reason':kind==='check-out'?'recipient':'warehouse')?.focus?.(),0)}
  const submitAction=async()=>{if(!action)return;try{const values=await actionForm.validateFields();setSaving(true);await api.post(`/warehouse/evidence/${action.row.id}/${action.kind}`,values);message.success({"check-in":'证物已入库',"check-out":'证物已出库',"recheck-in":'证物已重新入库',destroy:'证物已销毁'}[action.kind]);setAction(null);await load()}catch(error:any){if(error?.errorFields)return;message.error(error?.response?.data?.detail||'业务办理失败')}finally{setSaving(false)}}
  const openHistory=async(row:Item)=>{setHistoryRow(row);setHistory([]);try{const {data}=await api.get(`/records/${row.id}/history`);setHistory(data.items||[])}catch{message.error('流程记录加载失败')}}
  useEffect(()=>{const target=consumeBusinessRecordDetailTarget('warehouse');if(!target)return;void (async()=>{try{const {data}=await api.get(`/records/${target.id}`);if(data.module!=='warehouse')throw new Error('关联记录不是证物');await openHistory(data)}catch(error:any){message.error(error?.response?.data?.detail||error?.message||'证物详情加载失败')}})()},[])

  const openCaseDetail=async(caseNo:unknown)=>{const serialNo=String(caseNo||'').trim();if(!serialNo||serialNo==='—'){message.warning('当前证物未关联案件');return}try{const record=await resolveDetailRelation('case',{serial_no:serialNo});if(!record){message.warning('未找到关联案件或当前账号无权查看');return}rememberCaseDetailTarget({id:record.id,serial_no:record.serial_no});onNavigate?.('case-company')}catch(error:any){message.error(error?.response?.data?.detail||'关联案件加载失败')}}
  const openClueDetail=(clueNo:unknown)=>{const serialNo=String(clueNo||'').trim();if(!serialNo||serialNo==='—'){message.warning('当前证物未关联线索');return}rememberInvestigationDetailTarget({serial_no:serialNo,module:'clue'});onNavigate?.('clue-company-draft')}
  const openNotaryDetail=async(certificateNo:unknown)=>{const certificate=String(certificateNo||'').trim();if(!certificate||certificate==='—'){message.warning('当前证物未关联公证信息');return}try{const {data}=await api.get('/notaries/lookup',{params:{certificate_no:certificate}});rememberInvestigationDetailTarget({id:data.id,serial_no:data.serial_no,module:'notary'});onNavigate?.('notary')}catch(error:any){message.error(error?.response?.data?.detail||'关联公证加载失败')}}
  const openCustomerDetail=async(customerName:unknown)=>{const title=String(customerName||'').trim();if(!title||title==='—'){message.warning('当前证物未关联权利人');return}try{const {data}=await api.get('/records',{params:{module:'customer',keyword:title,page_size:100}});const customer=(data.items as Item[]).find(item=>item.title===title||item.customer===title);if(!customer){message.warning('未找到关联权利人档案或当前账号无权查看');return}rememberCustomerDetailTarget({id:customer.id,serial_no:customer.serial_no,title:customer.title});onNavigate?.('customer-company')}catch(error:any){message.error(error?.response?.data?.detail||'关联权利人加载失败')}}
  const rowMenu=(row:Item):MenuProps['items']=>{
    const rowStatus=statusOf(row)
    const items:MenuProps['items']=[{key:'history',label:'查看流程记录',onClick:()=>void openHistory(row)}]
    if(!['已出库','已销毁'].includes(rowStatus))items.push({key:'edit',label:'编辑证物资料',onClick:()=>openEditor(row)})
    if(rowStatus==='未入库')items.push({key:'check-in',label:'办理入库',onClick:()=>openAction('check-in',row)})
    if(['已入库','已重新入库'].includes(rowStatus))items.push({key:'check-out',label:'办理出库',onClick:()=>openAction('check-out',row)},{key:'destroy',danger:true,label:'销毁证物',onClick:()=>openAction('destroy',row)})
    if(rowStatus==='已出库')items.push({key:'recheck-in',label:'重新入库',onClick:()=>openAction('recheck-in',row)})
    return items
  }
  const columns:TableColumnsType<Item>=[
    {title:'库位',key:'location',width:120,sorter:(a,b)=>String(a.data.location||'').localeCompare(String(b.data.location||'')),render:(_v,row)=>row.data.location||'—'},
    {title:'线索编号',dataIndex:'serial_no',width:150,render:(value)=>value?<Button type="link" onClick={()=>openClueDetail(value)}>{value}</Button>:'—'},
    {title:'公证书号',key:'notary',width:150,render:(_v,row)=>row.data.notary_no?<Button type="link" onClick={()=>void openNotaryDetail(row.data.notary_no)}>{row.data.notary_no}</Button>:'—'},
    {title:'案件编号',key:'caseNo',width:145,render:(_v,row)=>row.data.case_no?<Button type="link" onClick={()=>openCaseDetail(row.data.case_no)}>{row.data.case_no}</Button>:'—'},
    {title:'货物出售店铺',key:'shop',width:180,render:(_v,row)=>row.data.shop_name||row.title||'—'},
    {title:'调查员',key:'investigator',width:110,render:(_v,row)=>row.data.investigator||row.owner||'—'},
    {title:'公证处',key:'notaryOffice',width:180,render:(_v,row)=>row.data.notary_office||'—'},
    {title:'权利人',key:'rightsHolder',width:160,render:(_v,row)=>row.data.rights_holder?<Button type="link" onClick={()=>void openCustomerDetail(row.data.rights_holder)}>{row.data.rights_holder}</Button>:'—'},
    {title:'取证日期',key:'date',width:115,render:(_v,row)=>row.data.evidence_date||row.data.collected_at||'—'},
    {title:'证物状态',key:'status',width:115,render:(_v,row)=><Tag color={statusColor[statusOf(row)]}>{statusOf(row)}</Tag>},
    {title:'',key:'action',width:45,fixed:'right',render:(_v,row)=><Dropdown trigger={['click']} menu={{items:rowMenu(row)}}><Button type="text" size="small" aria-label={`操作 ${row.serial_no}`} icon={<EllipsisOutlined/>}/></Dropdown>},
  ]

  const actionTitle=action?({"check-in":'证物入库',"check-out":'证物出库',"recheck-in":'证物重新入库',destroy:'销毁证物'}[action.kind]):''
  const selectStorageLocation=(keys:Key[])=>{
    const key=String(keys[0]||'')
    if(key.startsWith('warehouse:')){setWarehouse(key.slice('warehouse:'.length));setLocation('');return}
    if(key.startsWith('location:')){const [warehouseName,locationName]=key.slice('location:'.length).split('\u0000');setWarehouse(warehouseName);setLocation(locationName)}
  }

  return <Card className="panel warehouse-location" title="仓库库位">
    <div className="warehouse-layout">
      <aside className="warehouse-storage-tree" aria-label="仓库库位汇总">
        <div className="warehouse-storage-title"><span>仓库库位</span><Button type="link" size="small" onClick={()=>{setWarehouse('');setLocation('')}}>全部</Button></div>
        <Tree blockNode defaultExpandAll virtual={false} selectedKeys={[location?`location:${warehouse}\u0000${location}`:warehouse?`warehouse:${warehouse}`:'']} onSelect={selectStorageLocation} treeData={storageTreeData}/>
        {!storageTreeData.length&&<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无证物库位"/>}
      </aside>
      <section className="warehouse-list-panel">
      <div className="warehouse-list-title"><span>货物列表</span></div>
      <div className="warehouse-query">
        <label><span>仓库</span><Select value={warehouse} onChange={value=>{setWarehouse(value);setLocation('')}} options={[{value:'',label:'请选择'},...warehouseOptions.map(value=>({value,label:value}))]}/></label>
        <label><span>库位</span><Input value={location} onChange={e=>setLocation(e.target.value)} allowClear/></label>
        <label><span>权利人</span><Input value={rightsHolder} onChange={e=>setRightsHolder(e.target.value)} allowClear/></label>
        <label><span>证物状态</span><Select value={status} onChange={setStatus} options={[{value:'',label:'请选择'},...evidenceStatuses.map(value=>({value,label:value}))]}/></label>
        <label><span>案件编号</span><Input value={caseNo} onChange={e=>setCaseNo(e.target.value)} allowClear/></label>
        <label><span>店铺名称</span><Input value={shop} onChange={e=>setShop(e.target.value)} allowClear/></label>
        <label><span>调查员</span><Input value={investigator} onChange={e=>setInvestigator(e.target.value)} allowClear/></label>
        <label><span>公证书号</span><Input value={notaryNo} onChange={e=>setNotaryNo(e.target.value)} allowClear/></label>
        <label className="warehouse-date"><span>取证日期</span><DatePicker.RangePicker value={dates} onChange={value=>setDates(value as [Dayjs|null,Dayjs|null]|null)}/></label>
        <Space>
          <Button type="primary" onClick={()=>void load()}>查询</Button>
          <Button onClick={()=>openEditor()}>登记证物</Button>
        </Space>
      </div>
      <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={rows} locale={{emptyText:<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有查询到符合条件的记录 。"/>}} pagination={{pageSize:20,showTotal:total=>`共 ${total} 条`}} scroll={{x:1500}}/>
      </section>
    </div>

    <Modal width={760} title={editing?'编辑证物资料':'登记证物'} open={editorOpen} confirmLoading={saving} onCancel={()=>setEditorOpen(false)} onOk={()=>void saveEvidence()} okText="保存" cancelText="取消" destroyOnHidden>
      <Form form={form} layout="vertical" className="warehouse-evidence-form">
        <Form.Item label="线索编号" name="serial_no" rules={[{required:true,message:'请输入线索编号'}]}><Input/></Form.Item>
        <Form.Item label="仓库" name="warehouse" rules={[{required:true,message:'请选择仓库'}]}><Select options={warehouses.map(value=>({value,label:value}))}/></Form.Item>
        <Form.Item label="库位" name="location" rules={[{required:true,message:'请输入库位'}]}><Input/></Form.Item>
        <Form.Item label="公证书号" name="notary_no"><Input/></Form.Item>
        <Form.Item label="案件编号" name="case_no"><Input/></Form.Item>
        <Form.Item label="货物出售店铺" name="shop_name" rules={[{required:true,message:'请输入店铺名称'}]}><Input/></Form.Item>
        <Form.Item label="调查员" name="investigator" rules={[{required:true,message:'请输入调查员'}]}><Input/></Form.Item>
        <Form.Item label="公证处" name="notary_office"><Input/></Form.Item>
        <Form.Item label="权利人" name="rights_holder" rules={[{required:true,message:'请输入权利人'}]}><Input/></Form.Item>
        <Form.Item label="取证日期" name="evidence_date" rules={[{required:true,message:'请选择取证日期'}]}><DatePicker/></Form.Item>
        <Form.Item className="warehouse-form-wide" label="说明" name="description"><Input.TextArea rows={3} maxLength={1000} showCount/></Form.Item>
      </Form>
    </Modal>

    <Modal title={actionTitle} open={Boolean(action)} confirmLoading={saving} onCancel={()=>setAction(null)} onOk={()=>void submitAction()} okText="确认办理" okButtonProps={{danger:action?.kind==='destroy'}} destroyOnHidden>
      {action&&<><Descriptions size="small" column={1} bordered items={[{key:'serial',label:'线索编号',children:<Button type="link" onClick={()=>openClueDetail(action.row.serial_no)}>{action.row.serial_no}</Button>},{key:'shop',label:'货物出售店铺',children:String(action.row.data.shop_name||action.row.title)},{key:'status',label:'当前状态',children:<Tag color={statusColor[statusOf(action.row)]}>{statusOf(action.row)}</Tag>}]}/><Form form={actionForm} layout="vertical" className="warehouse-action-form">
        {(action.kind==='check-in'||action.kind==='recheck-in')&&<><Form.Item label="仓库" name="warehouse" rules={[{required:true,message:'请选择仓库'}]}><Select options={warehouses.map(value=>({value,label:value}))}/></Form.Item><Form.Item label="库位" name="location" rules={[{required:true,message:'请输入库位'}]}><Input/></Form.Item></>}
        {action.kind==='recheck-in'&&<Form.Item label="证物状况" name="condition" rules={[{required:true,message:'请输入证物状况'}]}><Input/></Form.Item>}
        {action.kind==='check-out'&&<><Form.Item label="领取人" name="recipient" rules={[{required:true,message:'请输入领取人'}]}><Input/></Form.Item><Form.Item label="出库用途" name="purpose" rules={[{required:true,message:'请输入出库用途'}]}><Input.TextArea rows={2}/></Form.Item></>}
        {action.kind==='destroy'?<Form.Item label="销毁原因" name="reason" rules={[{required:true,message:'请输入销毁原因'},{min:2,message:'销毁原因至少 2 个字符'}]}><Input.TextArea rows={3}/></Form.Item>:<Form.Item label="办理说明" name="comment"><Input.TextArea rows={2}/></Form.Item>}
      </Form></>}
    </Modal>

    <Modal width={720} title={`证物流程记录${historyRow?` · ${historyRow.serial_no}`:''}`} open={Boolean(historyRow)} footer={null} onCancel={()=>setHistoryRow(null)}>
      {historyRow&&<Descriptions size="small" column={2} bordered items={[{key:'shop',label:'货物出售店铺',children:String(historyRow.data.shop_name||historyRow.title)},{key:'status',label:'当前状态',children:<Tag color={statusColor[statusOf(historyRow)]}>{statusOf(historyRow)}</Tag>}]}/>} 
      {history.length?<Timeline className="warehouse-history" items={history.map(item=>({color:item.to_status==='已销毁'?'red':'green',children:<div><strong>{item.action}</strong> <Tag>{item.from_status||'起始'} → {item.to_status}</Tag><div>{item.operator} · {dayjs(item.created_at).format('YYYY-MM-DD HH:mm')}</div>{item.comment&&<div className="warehouse-history-comment">{item.comment}</div>}</div>}))}/>:<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无流程记录"/>}
    </Modal>
  </Card>
}
