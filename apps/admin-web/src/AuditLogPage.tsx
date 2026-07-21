import {useEffect, useState} from 'react'
import {Button, Card, Input, Select, Space, Table, Tag} from 'antd'
import {ReloadOutlined, SearchOutlined} from '@ant-design/icons'
import {api} from './api'
type Log={id:number;module:string;serial_no:string;title:string;action:string;from_status:string;to_status:string;operator:string;comment:string;created_at:string}
const labels:Record<string,string>={customer:'客户',contract:'合同',case:'案件',task:'任务',clue:'线索',notary:'公证',evidence:'证据',seal:'用印',finance:'财务',document:'收发文',hr:'人事',warehouse:'仓库',report:'报表'}
export default function AuditLogPage(){
 const [rows,setRows]=useState<Log[]>([]),[total,setTotal]=useState(0),[page,setPage]=useState(1),[loading,setLoading]=useState(false),[keyword,setKeyword]=useState(''),[module,setModule]=useState('')
 const load=async(p=page)=>{setLoading(true);try{const {data}=await api.get('/audit/events',{params:{module,keyword,page:p,page_size:50}});setRows(data.items);setTotal(data.total)}finally{setLoading(false)}}
 useEffect(()=>{load(1)},[])
 const columns=[{title:'时间',dataIndex:'created_at',width:165,render:(v:string)=>new Date(v).toLocaleString('zh-CN')},{title:'模块',dataIndex:'module',width:80,render:(v:string)=><Tag>{labels[v]||v}</Tag>},{title:'业务编号',dataIndex:'serial_no',width:175},{title:'业务标题',dataIndex:'title',width:220,ellipsis:true},{title:'操作',dataIndex:'action',width:130,render:(v:string)=><b>{v}</b>},{title:'状态变化',key:'status',width:180,render:(_:unknown,r:Log)=>r.from_status&&r.from_status!==r.to_status?<><Tag>{r.from_status}</Tag>→<Tag color="green">{r.to_status}</Tag></>:r.to_status||'—'},{title:'操作人',dataIndex:'operator',width:100},{title:'意见/说明',dataIndex:'comment',ellipsis:true}]
 return <Card className="panel" title="操作日志" extra={<Button icon={<ReloadOutlined/>} onClick={()=>load()}>刷新</Button>}><div className="filter-bar"><Input value={keyword} onChange={e=>setKeyword(e.target.value)} onPressEnter={()=>{setPage(1);load(1)}} allowClear prefix={<SearchOutlined/>} placeholder="编号、标题、操作人或意见"/><Select value={module||undefined} allowClear placeholder="全部模块" onChange={v=>setModule(v||'')} options={Object.entries(labels).map(([value,label])=>({value,label}))}/><Button type="primary" onClick={()=>{setPage(1);load(1)}}>查询</Button></div><Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={rows} scroll={{x:1350}} pagination={{current:page,total,pageSize:50,showTotal:n=>`共 ${n} 条`,onChange:p=>{setPage(p);load(p)}}}/></Card>
}
