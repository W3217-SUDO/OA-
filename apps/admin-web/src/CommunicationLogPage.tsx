import {useEffect, useState} from 'react'
import {Button, Card, DatePicker, Descriptions, Empty, Form, Input, message, Modal, Popconfirm, Select, Table} from 'antd'
import type {TableColumnsType} from 'antd'
import {PlusOutlined} from '@ant-design/icons'
import dayjs from 'dayjs'
import {api} from './api'
import {formatRequiredDate} from './formSafety'
import {rememberCustomerDetailTarget} from './customerDetailNavigation'
import './communication-log.css'

type Communication={id:number;customer_record_id:number;customer_name:string;contact:string;phone:string;content:string;occurred_at:string;operator:string;updated_at:string}
type Customer={id:number;serial_no:string;title:string;data:Record<string,unknown>}

export default function CommunicationLogPage({onNavigate}:{onNavigate?:(route:string)=>void}){
  const [rows,setRows]=useState<Communication[]>([])
  const [customers,setCustomers]=useState<Customer[]>([])
  const [customerName,setCustomerName]=useState('')
  const [dates,setDates]=useState<any>(null)
  const [mineOnly,setMineOnly]=useState(true)
  const [loading,setLoading]=useState(false)
  const [open,setOpen]=useState(false)
  const [editing,setEditing]=useState<Communication|null>(null)
  const [viewing,setViewing]=useState<Communication|null>(null)
  const [form]=Form.useForm()
  const isAdmin=(()=>{try{return JSON.parse(localStorage.getItem('user')||'{}').role==='admin'}catch{return false}})()

  const load=async()=>{
    setLoading(true)
    try{
      const {data}=await api.get('/communications',{params:{keyword:customerName,date_from:dates?.[0]?.format('YYYY-MM-DD'),date_to:dates?.[1]?.format('YYYY-MM-DD'),mine_only:isAdmin?mineOnly:true,page_size:100}})
      setRows(data.items)
    }catch(error:any){message.error(error?.response?.data?.detail||'沟通日志加载失败')}
    finally{setLoading(false)}
  }

  useEffect(()=>{
    void load()
    api.get('/records',{params:{module:'customer',page_size:100}}).then(({data})=>setCustomers(data.items)).catch(()=>message.error('客户列表加载失败'))
  },[])

  const startCreate=()=>{
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({occurred_at:dayjs()})
    setOpen(true)
  }
  const startView=(row:Communication)=>setViewing(row)
  const startEdit=(row:Communication)=>{
    setEditing(row)
    form.setFieldsValue({...row,occurred_at:dayjs(row.occurred_at)})
    setOpen(true)
  }
  const openCustomer=(customerId:number, customerName?:string)=>{
    const customer=customers.find(item=>item.id===customerId)
    rememberCustomerDetailTarget({id:customer?.id||customerId,serial_no:customer?.serial_no,title:customer?.title||customerName})
    onNavigate?.('customer-management')
  }
  const save=async()=>{
    try{
      const value=await form.validateFields()
      const payload={customer_record_id:value.customer_record_id,contact:value.contact||'',phone:value.phone||'',content:value.content,occurred_at:formatRequiredDate(value.occurred_at,'记录时间','YYYY-MM-DDTHH:mm:ss')}
      if(editing)await api.patch(`/communications/${editing.id}`,payload);else await api.post('/communications',payload)
      message.success(editing?'沟通记录已修改并同步到客户跟进':'沟通记录已新增并同步到客户跟进')
      setOpen(false)
      void load()
    }catch(error:any){if(error?.errorFields)return;message.error(error?.response?.data?.detail||error?.message||'保存失败')}
  }
  const remove=async(row:Communication)=>{try{await api.delete(`/communications/${row.id}`);message.success('沟通记录已删除并同步客户跟进');setOpen(false);setEditing(null);void load()}catch(error:any){message.error(error?.response?.data?.detail||'删除失败')}}
  const columns:TableColumnsType<Communication>=[
    {title:'用户',dataIndex:'operator',width:110},
    {title:'记录时间',dataIndex:'occurred_at',width:165,render:(value:string)=>new Date(value).toLocaleString('zh-CN',{hour12:false})},
    {title:'客户ID',dataIndex:'customer_record_id',width:160,ellipsis:true,align:'center',render:(value:number,row)=><Button className="communication-customer-id" type="link" title={String(customers.find(item=>item.id===value)?.serial_no||value)} onClick={()=>openCustomer(value,row.customer_name)}><span>{customers.find(item=>item.id===value)?.serial_no||value}</span></Button>},
    {title:'客户名称',dataIndex:'customer_name',width:260,ellipsis:true,render:(value:string,row)=><Button className="communication-customer-name" type="link" title={value} onClick={()=>openCustomer(row.customer_record_id,value)}><span>{value}</span></Button>},
    {title:'联系人',dataIndex:'contact',width:110,render:(value:string)=>value||'—'},
    {title:'联系电话',dataIndex:'phone',width:135,render:(value:string)=>value||'—'},
    {title:'内容',dataIndex:'content',width:320,ellipsis:true},
    {title:'操作',key:'action',width:185,render:(_value,row)=><><Button type="link" onClick={()=>startView(row)}>查看</Button><Button type="link" onClick={()=>startEdit(row)}>编辑</Button><Popconfirm title="确认删除该沟通记录？" onConfirm={()=>remove(row)}><Button type="link" danger>删除</Button></Popconfirm></>},
  ]

  return <>
    <Card className="panel communication-panel" title="沟通记录列表">
      <div className="communication-toolbar">
        <label><span>客户名称</span><Input value={customerName} onChange={event=>setCustomerName(event.target.value)} onPressEnter={load} allowClear/></label>
        <label><span>沟通时间</span><DatePicker.RangePicker value={dates} onChange={setDates}/></label>
        {isAdmin&&<label><span>数据范围</span><Select value={mineOnly?'mine':'all'} onChange={value=>setMineOnly(value==='mine')} options={[{value:'all',label:'全所沟通记录'},{value:'mine',label:'仅我的记录'}]}/></label>}
        <Button type="primary" onClick={load}>查询</Button>
        <Button type="primary" icon={<PlusOutlined/>} onClick={startCreate}>新增沟通记录</Button>
      </div>
      <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={rows} locale={{emptyText:<div className="communication-empty"><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据"/><Button type="primary" icon={<PlusOutlined/>} onClick={startCreate}>新增沟通记录</Button></div>}} pagination={{pageSize:15,showTotal:total=>`共 ${total} 条`}} tableLayout="fixed" scroll={{x:1445}}/>
    </Card>

    <Modal open={open} title={editing?'编辑沟通记录':'新增沟通记录'} okText="保存" cancelText="取消" onOk={save} onCancel={()=>setOpen(false)} destroyOnHidden width={680}>
      <Form form={form} layout="vertical">
          <div className="communication-form-grid">
            <Form.Item className="span-2" name="customer_record_id" label="客户" rules={[{required:true,message:'请选择客户'}]}><Select showSearch optionFilterProp="label" options={customers.map(item=>({value:item.id,label:`${item.title}（${item.serial_no}）`}))}/></Form.Item>
            <Form.Item name="contact" label="联系人"><Input/></Form.Item>
            <Form.Item name="phone" label="联系电话"><Input/></Form.Item>
            <Form.Item className="span-2" name="occurred_at" label="记录时间" rules={[{required:true,message:'请选择记录时间'}]}><DatePicker showTime style={{width:'100%'}}/></Form.Item>
            <Form.Item className="span-2" name="content" label="沟通内容" rules={[{required:true,message:'请输入沟通内容'},{max:4000}]}><Input.TextArea rows={5} showCount maxLength={4000}/></Form.Item>
          </div>
        </Form>{editing&&<div className="communication-history">{rows.filter(item=>item.customer_record_id===editing.customer_record_id).map(item=><div key={item.id}><time>{new Date(item.occurred_at).toLocaleString('zh-CN',{hour12:false})}</time><span>{item.contact} {item.phone} {item.content}</span></div>)}</div>}
    </Modal>

    <Modal open={Boolean(viewing)} title="查看沟通记录" onCancel={()=>setViewing(null)} footer={<Button onClick={()=>setViewing(null)}>关闭</Button>} destroyOnHidden width={680}>
      {viewing&&<Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="客户ID"><Button type="link" onClick={()=>openCustomer(viewing.customer_record_id,viewing.customer_name)}>{customers.find(item=>item.id===viewing.customer_record_id)?.serial_no||viewing.customer_record_id}</Button></Descriptions.Item>
        <Descriptions.Item label="客户名称"><Button type="link" onClick={()=>openCustomer(viewing.customer_record_id,viewing.customer_name)}>{viewing.customer_name}</Button></Descriptions.Item>
        <Descriptions.Item label="联系人">{viewing.contact||'—'}</Descriptions.Item>
        <Descriptions.Item label="联系电话">{viewing.phone||'—'}</Descriptions.Item>
        <Descriptions.Item label="记录时间">{new Date(viewing.occurred_at).toLocaleString('zh-CN',{hour12:false})}</Descriptions.Item>
        <Descriptions.Item label="记录用户">{viewing.operator||'—'}</Descriptions.Item>
        <Descriptions.Item label="沟通内容" span={2}><span style={{whiteSpace:'pre-wrap'}}>{viewing.content||'—'}</span></Descriptions.Item>
      </Descriptions>}
    </Modal>
  </>
}
