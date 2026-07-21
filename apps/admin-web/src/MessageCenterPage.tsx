import {useEffect, useMemo, useState} from 'react'
import {Button, Card, DatePicker, Drawer, Empty, Form, Input, message, Modal, Popconfirm, Select, Space, Table, Tabs, Tag} from 'antd'
import type {TableColumnsType} from 'antd'
import type {Key} from 'react'
import {DeleteOutlined, MailOutlined, PlusOutlined} from '@ant-design/icons'
import type {Dayjs} from 'dayjs'
import {api} from './api'
import './message-center.css'

type Notice={id:number;sender:string;recipient:string;notification_type:string;title:string;content:string;level:string;is_read:boolean;read_at:string|null;created_at:string}
type DirectoryUser={username:string;display_name:string;department:string}

const levelColors:Record<string,string>={error:'red',warning:'orange',info:'blue'}
const tabItems=[
  {key:'all',label:'全部消息'},
  {key:'unread',label:'未读消息'},
  {key:'read',label:'已读消息'},
  {key:'sent',label:'已发送消息'},
]

export default function MessageCenterPage(){
  const [view,setView]=useState('all')
  const [rows,setRows]=useState<Notice[]>([])
  const [loading,setLoading]=useState(false)
  const [keyword,setKeyword]=useState('')
  const [sender,setSender]=useState('')
  const [type,setType]=useState('')
  const [dates,setDates]=useState<[Dayjs|null,Dayjs|null]|null>(null)
  const [selectedKeys,setSelectedKeys]=useState<Key[]>([])
  const [selected,setSelected]=useState<Notice|null>(null)
  const [directory,setDirectory]=useState<DirectoryUser[]>([])
  const [composeOpen,setComposeOpen]=useState(false)
  const [composeForm]=Form.useForm()

  const params=useMemo(()=>({
    sent_only:view==='sent',
    read_status:view==='unread'?'未读':view==='read'?'已读':'',
    keyword,
    sender,
    notification_type:type,
    date_from:dates?.[0]?.format('YYYY-MM-DD'),
    date_to:dates?.[1]?.format('YYYY-MM-DD'),
  }),[view,keyword,sender,type,dates])

  const load=async()=>{
    setLoading(true)
    try{
      const {data}=await api.get('/notifications',{params})
      setRows(data.items)
      setSelectedKeys([])
    }catch(error:any){message.error(error?.response?.data?.detail||'消息加载失败')}
    finally{setLoading(false)}
  }

  useEffect(()=>{void load()},[view])
  useEffect(()=>{api.get('/users/directory').then(({data})=>setDirectory(data.items)).catch(()=>message.error('通讯录加载失败'))},[])

  const openNotice=async(row:Notice)=>{
    let current=row
    if(view!=='sent'&&!row.is_read){
      try{
        const {data}=await api.post(`/notifications/${row.id}/read`)
        current=data
        setRows(items=>items.map(item=>item.id===row.id?data:item))
      }catch(error:any){message.warning(error?.response?.data?.detail||'消息已打开，但标记已读失败')}
    }
    setSelected(current)
  }

  const markSelectedRead=async()=>{
    if(!selectedKeys.length){message.warning('请先选择消息');return}
    try{
      const unread=rows.filter(item=>selectedKeys.includes(item.id)&&!item.is_read)
      await Promise.all(unread.map(item=>api.post(`/notifications/${item.id}/read`)))
      message.success('所选消息已标记为已读')
      await load()
    }catch(error:any){message.error(error?.response?.data?.detail||'标记已读失败')}
  }
  const markAllRead=async()=>{try{const {data}=await api.post('/notifications/read-all');message.success(`已标记 ${data.updated} 条消息为已读`);await load()}catch(error:any){message.error(error?.response?.data?.detail||'全部标记已读失败')}}
  const sendMessage=async()=>{const value=await composeForm.validateFields();try{const {data}=await api.post('/notifications/send',value);message.success(`消息已发送给 ${data.sent} 人`);setComposeOpen(false);composeForm.resetFields();if(view==='sent')await load()}catch(error:any){message.error(error?.response?.data?.detail||'消息发送失败')}}
  const deleteMessages=async(ids:Key[])=>{if(!ids.length)return;try{await Promise.all(ids.map(id=>api.delete(`/notifications/${id}`)));message.success(`已删除 ${ids.length} 条消息`);setSelected(null);setSelectedKeys([]);await load()}catch(error:any){message.error(error?.response?.data?.detail||'消息删除失败')}}

  const columns:TableColumnsType<Notice>=[
    {title:'序号',key:'sequence',width:62,align:'center',render:(_value,_row,index)=>index+1},
    {title:'发送者',dataIndex:'sender',width:105,ellipsis:true},
    {title:'接收者',dataIndex:'recipient',width:105,ellipsis:true},
    {title:'标题',dataIndex:'title',width:190,ellipsis:true,render:(value:string,row)=><Button type="link" className="message-title" onClick={()=>openNotice(row)}>{value}</Button>},
    {title:'内容',dataIndex:'content',ellipsis:true},
    {title:'提交时间',dataIndex:'created_at',width:160,sorter:(a,b)=>new Date(a.created_at).getTime()-new Date(b.created_at).getTime(),render:(value:string)=>new Date(value).toLocaleString('zh-CN',{hour12:false})},
    {title:'类型',dataIndex:'notification_type',width:92,render:(value:string,row)=><Tag color={levelColors[row.level]||'blue'}>{value}</Tag>},
    {title:'操作',key:'action',width:125,render:(_value,row)=><Space size={0}><Button type="link" onClick={()=>openNotice(row)}>查看</Button><Popconfirm title="确认删除该消息？" onConfirm={()=>deleteMessages([row.id])}><Button type="link" danger icon={<DeleteOutlined/>}/></Popconfirm></Space>},
  ]

  return <>
    <Card className="panel message-center-panel" title="站内消息">
      <Tabs activeKey={view} onChange={setView} items={tabItems}/>
      <section className="message-list-panel">
        <div className="message-list-title">消息列表</div>
        <div className="message-filters">
          <label><span>消息时间</span><DatePicker.RangePicker value={dates} onChange={value=>setDates(value as [Dayjs|null,Dayjs|null]|null)}/></label>
          <label><span>发送人</span><Input value={sender} onChange={event=>setSender(event.target.value)} allowClear/></label>
          <label><span>消息关键字</span><Input value={keyword} onChange={event=>setKeyword(event.target.value)} onPressEnter={load} allowClear placeholder="消息内容"/></label>
          <label><span>消息类型</span><Select value={type} onChange={setType} options={[{value:'',label:'全部'},{value:'系统通知',label:'系统通知'},{value:'用户通知',label:'用户通知'}]}/></label>
          <Button type="primary" onClick={load}>查询</Button><Button type="primary" icon={<PlusOutlined/>} onClick={()=>setComposeOpen(true)}>发送消息</Button>
        </div>
        <Table rowKey="id" size="small" loading={loading} rowSelection={{selectedRowKeys:selectedKeys,onChange:setSelectedKeys,columnWidth:42}} columns={columns} dataSource={rows} locale={{emptyText:<Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据"/>}} pagination={{pageSize:15,showTotal:total=>`共 ${total} 条`}} scroll={{x:1120}}/>
        <div className="message-table-actions">{view!=='sent'&&<><Button disabled={!selectedKeys.length} onClick={markSelectedRead}>标记已读</Button><Button onClick={markAllRead}>全部标记已读</Button></>}<Popconfirm title="确认删除选中的消息？" onConfirm={()=>deleteMessages(selectedKeys)}><Button danger disabled={!selectedKeys.length}>删除选中</Button></Popconfirm></div>
      </section>
    </Card>
    <Drawer open={Boolean(selected)} width={520} title={<Space><MailOutlined/>{selected?.title}</Space>} onClose={()=>setSelected(null)}>
      <p><Tag>{selected?.notification_type}</Tag><Tag color={selected?.is_read?'default':'red'}>{selected?.is_read?'已读':'未读'}</Tag></p>
      <p>发送者：{selected?.sender}</p><p>接收者：{selected?.recipient}</p>
      <p>时间：{selected?.created_at?new Date(selected.created_at).toLocaleString('zh-CN',{hour12:false}):''}</p>
      <Card size="small"><div className="message-content">{selected?.content}</div></Card>
    </Drawer>
    <Modal open={composeOpen} title="发送站内消息" okText="发送" cancelText="取消" onOk={sendMessage} onCancel={()=>setComposeOpen(false)} destroyOnHidden><Form form={composeForm} layout="vertical"><Form.Item name="recipients" label="接收人" rules={[{required:true,message:'请选择接收人'}]}><Select mode="multiple" showSearch optionFilterProp="label" options={directory.map(user=>({value:user.username,label:`${user.display_name}（${user.username}｜${user.department}）`}))}/></Form.Item><Form.Item name="title" label="标题" rules={[{required:true},{max:200}]}><Input/></Form.Item><Form.Item name="content" label="消息内容" rules={[{required:true},{max:4000}]}><Input.TextArea rows={6} showCount maxLength={4000}/></Form.Item></Form></Modal>
  </>
}
