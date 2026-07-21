import {useRef, useState} from 'react'
import {Button, message, Modal, Space, Table, Tag} from 'antd'
import {DownloadOutlined, UploadOutlined} from '@ant-design/icons'
import {api} from './api'

type ImportError={row:number;error:string;value?:string}
type ImportResult={module:string;created:number;failed:number;errors:ImportError[]}

const labels:Record<string,string>={contract:'合同',case:'案件',task:'任务',document:'收发文',finance:'费用',hr:'员工',warehouse:'物品',seal:'用印申请'}

export default function RecordImportButton({module,onImported}:{module:string;onImported:()=>void}){
  const inputRef=useRef<HTMLInputElement>(null)
  const [loading,setLoading]=useState(false)
  const downloadTemplate=async()=>{try{const {data}=await api.get('/records/import-template',{params:{module},responseType:'blob'});const url=URL.createObjectURL(data);const anchor=document.createElement('a');anchor.href=url;anchor.download=`${labels[module]||module}-导入模板.csv`;anchor.click();URL.revokeObjectURL(url)}catch(error:any){message.error(error?.response?.data?.detail||'模板下载失败')}}
  const importFile=async(file?:File)=>{if(!file)return;setLoading(true);const form=new FormData();form.append('file',file);try{const {data}=await api.post<ImportResult>('/records/import',form,{params:{module}});if(data.failed){Modal.info({width:680,title:`${labels[module]||module}批量导入结果`,content:<><p>成功 <Tag color="green">{data.created}</Tag> 条，失败 <Tag color="red">{data.failed}</Tag> 条。失败行未写入数据库。</p><Table rowKey={row=>`${row.row}-${row.error}`} size="small" pagination={false} dataSource={data.errors} columns={[{title:'行号',dataIndex:'row',width:70},{title:'业务编号',dataIndex:'value',width:150,render:(value:string)=>value||'—'},{title:'失败原因',dataIndex:'error'}]} scroll={{y:320}}/></>})}else{message.success(`批量导入完成：成功 ${data.created} 条`)}onImported()}catch(error:any){message.error(error?.response?.data?.detail||'批量导入失败')}finally{setLoading(false);if(inputRef.current)inputRef.current.value=''}}
  return <Space size={4}><input ref={inputRef} hidden type="file" accept=".csv,text/csv" onChange={event=>importFile(event.target.files?.[0])}/><Button icon={<DownloadOutlined/>} onClick={downloadTemplate}>导入模板</Button><Button icon={<UploadOutlined/>} loading={loading} onClick={()=>inputRef.current?.click()}>批量导入</Button></Space>
}
