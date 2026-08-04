import {useEffect, useMemo, useState} from 'react'
import {Alert, Button, Card, Form, Input, message, Select, Tabs} from 'antd'
import {SaveOutlined} from '@ant-design/icons'
import {api} from './api'
import './user-center.css'

type Profile={id:number;username:string;display_name:string;department:string;role:string;is_active:boolean;created_at:string;email?:string;office_phone?:string;mobile?:string;menu_auto_collapse?:'yes'|'no'}
type BasicProfile={email:string;office_phone:string;mobile:string}
type Preferences={auto_collapse:'yes'|'no'}

const defaultPreferences:Preferences={auto_collapse:'no'}

export default function UserCenterPage(){
  const [profile,setProfile]=useState<Profile|null>(null)
  const [loading,setLoading]=useState(false)
  const [basicForm]=Form.useForm<BasicProfile>()
  const [passwordForm]=Form.useForm()
  const [preferenceForm]=Form.useForm<Preferences>()
  const storagePrefix=useMemo(()=>`sunhold:user-settings:${profile?.username||'current'}`,[profile?.username])

  const load=async()=>{
    setLoading(true)
    try{
      const {data}=await api.get('/auth/me')
      setProfile(data)
      basicForm.setFieldsValue({email:data.email||'',office_phone:data.office_phone||'',mobile:data.mobile||''})
      preferenceForm.setFieldsValue({auto_collapse:data.menu_auto_collapse||'no'})
    }catch{message.error('用户资料加载失败')}
    finally{setLoading(false)}
  }

  useEffect(()=>{void load()},[])

  const saveBasic=async()=>{
    const values=await basicForm.validateFields()
    try{
      const {data}=await api.patch('/auth/me',values)
      setProfile(data)
      message.success('基本资料保存成功')
    }catch(error:any){message.error(error?.response?.data?.detail||'基本资料保存失败')}
  }

  const changePassword=async()=>{
    const values=await passwordForm.validateFields()
    try{
      await api.patch('/auth/me',{current_password:values.current_password,new_password:values.new_password})
      passwordForm.resetFields()
      message.success('密码修改成功，下次登录请使用新密码')
    }catch(error:any){message.error(error?.response?.data?.detail||'密码修改失败')}
  }

  const savePreferences=async()=>{
    const values=await preferenceForm.validateFields()
    try{
      await api.patch('/auth/me',{menu_auto_collapse:values.auto_collapse})
      localStorage.setItem(`${storagePrefix}:preferences`,JSON.stringify(values))
      localStorage.setItem('sunhold:sidebar-auto-collapse',values.auto_collapse)
      window.dispatchEvent(new CustomEvent('sunhold:preferences-updated',{detail:values}))
      message.success('个性配置保存成功')
    }catch(error:any){message.error(error?.response?.data?.detail||'个性配置保存失败')}
  }

  const tabItems=[
    {key:'basic',label:'基本资料',children:<section className="account-setting-section">
      <div className="account-setting-title">基本资料设置</div>
      <div className="account-setting-help">请完善以下信息,方便我们更好的为您服务</div>
      <Form form={basicForm} className="account-setting-form" labelCol={{flex:'100px'}} wrapperCol={{flex:'360px'}} labelAlign="right" colon>
        <Form.Item label="Email" name="email" rules={[{required:true,message:'请输入 Email'},{type:'email',message:'请输入正确的 Email 地址'},{max:128}]}><Input maxLength={128}/></Form.Item>
        <Form.Item label="办公电话" name="office_phone" rules={[{required:true,message:'请输入办公电话'},{max:32}]}><Input maxLength={32}/></Form.Item>
        <Form.Item label="手机" name="mobile" rules={[{required:true,message:'请输入手机号码'},{pattern:/^[0-9+\-\s()]*$/,message:'请输入正确的手机号码'},{max:32}]}><Input maxLength={32}/></Form.Item>
        <Form.Item label=" "><Button type="primary" icon={<SaveOutlined/>} onClick={saveBasic}>保存</Button></Form.Item>
      </Form>
    </section>},
    {key:'password',label:'密码修改',children:<section className="account-setting-section">
      <div className="account-setting-title">密码设置</div>
      <div className="account-setting-help">请完善以下信息,方便我们更好的为您服务</div>
      <Form form={passwordForm} className="account-setting-form" labelCol={{flex:'100px'}} wrapperCol={{flex:'360px'}} labelAlign="right" colon>
        <Form.Item label="原密码" name="current_password" rules={[{required:true,message:'请输入原密码'}]}><Input.Password autoComplete="current-password"/></Form.Item>
        <Form.Item label="新密码" name="new_password" rules={[{required:true,message:'请输入新密码'},{min:8,message:'密码至少 8 位'},({getFieldValue})=>({validator(_,value){return !value||!getFieldValue('current_password')||value!==getFieldValue('current_password')?Promise.resolve():Promise.reject(new Error('新密码不能与原密码相同'))}})]}><Input.Password autoComplete="new-password"/></Form.Item>
        <Form.Item label="新密码确认" name="confirm_password" dependencies={['new_password']} rules={[{required:true,message:'请再次输入新密码'},({getFieldValue})=>({validator(_,value){return !value||getFieldValue('new_password')===value?Promise.resolve():Promise.reject(new Error('两次输入的新密码不一致'))}})]}><Input.Password autoComplete="new-password"/></Form.Item>
        <Form.Item label=" "><Button type="primary" icon={<SaveOutlined/>} onClick={changePassword}>保存</Button></Form.Item>
      </Form>
    </section>},
    {key:'preferences',label:'个性配置',children:<section className="account-setting-section">
      <div className="account-setting-title">个性配置</div>
      <div className="account-setting-help">请完善以下信息,方便我们更好的为您服务</div>
      <Form form={preferenceForm} className="account-setting-form preference-form" initialValues={defaultPreferences} labelCol={{flex:'160px'}} wrapperCol={{flex:'360px'}} labelAlign="right" colon>
        <Form.Item label="左侧菜单自动收缩" name="auto_collapse" rules={[{required:true}]}><Select options={[{value:'yes',label:'是'},{value:'no',label:'否'}]}/></Form.Item>
        <Form.Item label=" "><Button type="primary" icon={<SaveOutlined/>} onClick={savePreferences}>保存</Button></Form.Item>
      </Form>
    </section>},
  ]

  return <Card className="panel user-account-panel" title="账户管理" loading={loading}>
    {profile&&<Alert type={profile.role==='admin'?'warning':'info'} showIcon message={`${profile.display_name}（${profile.username}）｜${profile.role==='admin'?'系统管理员·最高权限':profile.role==='manager'?'部门负责人':profile.role==='auditor'?'审计人员':'普通用户'}｜${profile.department}`} style={{marginBottom:12}}/>}
    <Tabs items={tabItems}/>
  </Card>
}
