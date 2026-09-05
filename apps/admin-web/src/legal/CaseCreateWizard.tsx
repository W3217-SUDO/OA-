import { EditOutlined } from "@ant-design/icons";
import type { FormInstance } from "antd";
import { Button,Checkbox,DatePicker,Form,Input,Select,Space,Steps } from "antd";
import dayjs from "dayjs";
import { resolveCaseSourcePerson } from "../caseContractPrefill";
import type { CaseRow,ContractRow } from "./types";

interface LitigantLabels {
  plaintiff: string;
  plaintiffAgent: string;
  defendant: string;
  defendantAgent: string;
  third: string;
  thirdAgent: string;
}

interface CaseCreateWizardProps {
  createFlowToken: string;
  createStep: number;
  setCreateStep: (step: number) => void;
  createForm: FormInstance;
  createSubmitting: boolean;
  isCounselCreate: boolean;
  isCriminalCreate: boolean;
  isAdministrativeCreate: boolean;
  initialView: string;
  caseTypeOptions: { value: string; label: string }[];
  setSelectedCreateType: (value: string) => void;
  contractPrefill: { id: number; serial_no: string; title: string; customer: string } | null;
  contracts: ContractRow[];
  createCustomer: string;
  createContractOptions: { value: number; label: string }[];
  clientPositionOptions: string[];
  caseStatuses: string[];
  causeOptions: { value: string; label: string }[];
  caseLawyerOptions: { value: string; label: string }[];
  caseAssistantOptions: { value: string; label: string }[];
  caseClues: CaseRow[];
  rightTypeOptions: { value: string; label: string }[];
  litigantLabels: LitigantLabels;
  firstCourtEnabled: boolean;
  secondCourtEnabled: boolean;
  retrialCourtEnabled: boolean;
  firstCourtName: string;
  secondCourtName: string;
  retrialCourtName: string;
  courtOptions: { value: string; label: string; code?: string }[];
  officersForCourt: (courtName: string | undefined, role: string) => { value: string; label: string }[];
  openCreateDefendantEditor: () => void;
  advanceCreateStep: () => Promise<void>;
  saveLitigants: (complete: boolean) => Promise<void>;
  finishCreateFlow: () => Promise<void>;
}

export const CaseCreateWizard = ({
  createFlowToken,
  createStep,
  setCreateStep,
  createForm,
  createSubmitting,
  isCounselCreate,
  isCriminalCreate,
  isAdministrativeCreate,
  initialView,
  caseTypeOptions,
  setSelectedCreateType,
  contractPrefill,
  contracts,
  createCustomer,
  createContractOptions,
  clientPositionOptions,
  caseStatuses,
  causeOptions,
  caseLawyerOptions,
  caseAssistantOptions,
  caseClues,
  rightTypeOptions,
  litigantLabels,
  firstCourtEnabled,
  secondCourtEnabled,
  retrialCourtEnabled,
  firstCourtName,
  secondCourtName,
  retrialCourtName,
  courtOptions,
  officersForCourt,
  openCreateDefendantEditor,
  advanceCreateStep,
  saveLitigants,
  finishCreateFlow,
}: CaseCreateWizardProps) => {
  const resolveCasePersonValue = (source: string) => {
    const normalized = String(source || "").trim();
    if (!normalized) return "";
    const option = caseAssistantOptions.find((item) =>
      item.value === normalized || item.label === normalized || item.label.startsWith(`${normalized}（`),
    );
    return option?.value || normalized;
  };
  return (
    <div className="case-create-route-page" data-flow-token={createFlowToken}>
      <Steps
        className="case-create-steps"
        current={createStep}
        items={isCounselCreate
          ? [{ title: "基本信息" }, { title: "当事人信息" }]
          : [{ title: "基本信息" }, { title: "当事人信息" }, { title: "司法机关信息" }]}
      />
      <Form
        form={createForm}
        className="case-create-wizard-form"
        labelCol={{ span: 5 }}
        wrapperCol={{ span: 17 }}
      >
        {createStep === 0 && (
          <div className="case-create-step">
            <div className="case-create-section-title">基本信息</div>
            <div className="case-create-fields">
              <Form.Item label="案件类型" name="case_type" rules={[{ required: true, message: "请选择案件类型" }]}>
                <Select
                  options={caseTypeOptions}
                  disabled={initialView !== "case-new"}
                  onChange={(value:string)=>{
                    setSelectedCreateType(value);
                    createForm.setFieldsValue({client_position:value==="刑事案件"?"被告人/犯罪嫌疑人":value==="法律顾问"?"":"原告/申请人",cause_or_charge:undefined,right_type:undefined,counsel_type:undefined,counsel_range:value==="法律顾问"?[dayjs(),dayjs().add(1,"year")]:undefined});
                  }}
                />
              </Form.Item>
              <Form.Item label="客户" name="customer" rules={[{ required: true, message: "请选择客户" }]}>
                <Select disabled={Boolean(contractPrefill?.id)} showSearch optionFilterProp="label" placeholder="请选择客户" options={[...new Set(contracts.map((row) => row.customer))].map((value) => ({ value, label: value }))} onChange={()=>createForm.setFieldsValue({contract_record_id:undefined,source_person:undefined,title:undefined})} />
              </Form.Item>
              {!isCounselCreate && <Form.Item label="客户诉讼地位" name="client_position" rules={[{ required: true }]}>
                <Select options={clientPositionOptions.map((value) => ({ value, label: value }))} />
              </Form.Item>}
              <Form.Item label="合同号" name="contract_record_id" rules={[{ required: true, message: "请选择已审批合同" }]}>
                <Select disabled={Boolean(contractPrefill?.id) || !String(createCustomer || "").trim()} showSearch allowClear optionFilterProp="label" placeholder="请选择合同" notFoundContent={createCustomer ? "该客户下暂无可用于新建案件的合同" : "请先选择客户"} options={createContractOptions} onChange={(value:number|undefined)=>{const selected=contracts.find(row=>row.id===value);createForm.setFieldsValue({customer:selected?.customer,source_person:resolveCasePersonValue(resolveCaseSourcePerson(selected)),title:selected?`${selected.title}案件`:undefined})}} />
              </Form.Item>
              <Form.Item label="案源人" name="source_person"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="由关联合同自动带入，可按本案实际情况修改" /></Form.Item>
              {!isCounselCreate && <Form.Item label={isCriminalCreate ? "罪名" : "案由"} name="cause_or_charge" rules={[{ required: true }]}>{isCriminalCreate?<Input placeholder="请输入罪名" />:<Select showSearch optionFilterProp="label" placeholder="输入关键词选择案由" options={causeOptions}/>}</Form.Item>}
              {isCounselCreate && <><Form.Item label="顾问类型" name="counsel_type" rules={[{ required: true }]}><Input placeholder="请输入顾问类型" /></Form.Item><Form.Item label="顾问期限" name="counsel_range" rules={[{ required: true }]}><DatePicker.RangePicker style={{ width: "100%" }} /></Form.Item></>}
              <Form.Item label="案件名称" name="title" rules={[{ required: true }]}><Input placeholder="请输入案件名称" /></Form.Item>
              {!isCounselCreate && <Form.Item label="案件阶段" name="status"><Select disabled options={caseStatuses.map((value) => ({ value, label: value === "新案待分配" ? "待分配" : value }))} /></Form.Item>}
              <Form.Item label="经办律师" name="handling_lawyers" rules={[{ required: true, message: "请选择系统已创建的在职律师" }]}><Select mode="multiple" disabled={createStep === 0} showSearch optionFilterProp="label" options={caseLawyerOptions} placeholder="创建人自动作为经办律师" notFoundContent="暂无在职律师；请先在人事中心创建并启用律师账号" /></Form.Item>
              <Form.Item label="律师助理" name="assistant"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="请选择系统已创建的在职人员" /></Form.Item>
              {!isCounselCreate && <><Form.Item label="调查员" name="investigator"><Select allowClear showSearch optionFilterProp="label" options={caseAssistantOptions} placeholder="可选，选择调查员" /></Form.Item><Form.Item label="调查线索" name="investigation_clue"><Select allowClear showSearch optionFilterProp="label" options={caseClues.filter((item) => item.status !== "已转案件").map((item) => ({ value: item.serial_no, label: `${item.serial_no}｜${item.title}` }))} placeholder="可选，选择调查线索" /></Form.Item></>}
              {!isCriminalCreate && !isCounselCreate && <Form.Item label="权利类型" name="right_type"><Select allowClear showSearch optionFilterProp="label" placeholder="请选择权利类型" options={rightTypeOptions} /></Form.Item>}
            </div>
          </div>
        )}
        {createStep === 1 && (
          <div className="case-create-step"><div className="case-create-section-title">当事人信息</div><div className="case-create-fields">
            <Form.Item label={litigantLabels.plaintiff} name="plaintiffs"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
            <Form.Item label={litigantLabels.plaintiffAgent} name="plaintiff_agents"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
            <Form.Item label={litigantLabels.defendant} required={!isCounselCreate}>
              <Space.Compact block>
                <Form.Item name="defendants" noStyle rules={[{ required: true, message: "请输入至少一名被告" }]}>
                  <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" style={{ width: "calc(100% - 90px)" }} />
                </Form.Item>
                <Button icon={<EditOutlined />} onClick={openCreateDefendantEditor}>编辑被告</Button>
              </Space.Compact>
            </Form.Item>
            <Form.Item label={litigantLabels.defendantAgent} name="defendant_agents"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
            <Form.Item label={litigantLabels.third} name="third_parties"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
            <Form.Item label={litigantLabels.thirdAgent} name="third_party_agents"><Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入名称后回车，可添加多人" /></Form.Item>
            <Form.Item label="备注" name="litigant_comment"><Input.TextArea rows={3} /></Form.Item>
          </div></div>
        )}
        {createStep === 2 && !isCounselCreate && (
          <div className="case-create-step"><div className="case-create-section-title">司法机关信息</div><div className="case-create-fields">
            {isCriminalCreate && <><div className="case-create-section-title">公安机关</div>
            <Form.Item label="公安机关" name="public_security_name"><Input /></Form.Item><Form.Item label="案件编号" name="public_security_case_no"><Input /></Form.Item><Form.Item label="地址" name="public_security_address"><Input /></Form.Item><Form.Item label="联系电话" name="public_security_phone"><Input /></Form.Item><Form.Item label="承办人" name="public_security_operator"><Input /></Form.Item>
            <div className="case-create-section-title">一审检察院</div>
            <Form.Item label="检察院" name="first_procuratorate_name"><Input /></Form.Item><Form.Item label="案件编号" name="first_procuratorate_case_no"><Input /></Form.Item><Form.Item label="地址" name="first_procuratorate_address"><Input /></Form.Item><Form.Item label="联系电话" name="first_procuratorate_phone"><Input /></Form.Item><Form.Item label="承办人" name="first_procuratorate_operator"><Input /></Form.Item>
            <div className="case-create-section-title">二审检察院</div>
            <Form.Item label="检察院" name="second_procuratorate_name"><Input /></Form.Item><Form.Item label="案件编号" name="second_procuratorate_case_no"><Input /></Form.Item><Form.Item label="地址" name="second_procuratorate_address"><Input /></Form.Item><Form.Item label="联系电话" name="second_procuratorate_phone"><Input /></Form.Item><Form.Item label="承办人" name="second_procuratorate_operator"><Input /></Form.Item>
            <div className="case-create-section-title">再审检察院</div>
            <Form.Item label="检察院" name="retrial_procuratorate_name"><Input /></Form.Item><Form.Item label="案件编号" name="retrial_procuratorate_case_no"><Input /></Form.Item><Form.Item label="地址" name="retrial_procuratorate_address"><Input /></Form.Item><Form.Item label="联系电话" name="retrial_procuratorate_phone"><Input /></Form.Item><Form.Item label="承办人" name="retrial_procuratorate_operator"><Input /></Form.Item></>}
            <Form.Item name="first_court_enabled" valuePropName="checked" wrapperCol={{ offset: 5, span: 17 }}><Checkbox>一审法院信息</Checkbox></Form.Item>
            {firstCourtEnabled && <><Form.Item label="法院" name="first_court_name"><Select showSearch optionFilterProp="label" options={courtOptions}/></Form.Item><Form.Item label="法庭" name="first_court_courtroom"><Input /></Form.Item><Form.Item label="法官" name="first_court_judge"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(firstCourtName, "法官")} placeholder="请先选择法院" /></Form.Item><Form.Item label="书记员" name="first_court_clerk"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(firstCourtName, "书记员")} placeholder="请先选择法院" /></Form.Item><Form.Item label="案号" name="first_court_case_no"><Input /></Form.Item><Form.Item label="立案日期" name="first_court_filing_date"><DatePicker style={{ width: "100%" }} /></Form.Item><Form.Item label="开庭日期" name="first_court_hearing_date"><DatePicker style={{ width: "100%" }} /></Form.Item></>}
            <Form.Item name="second_court_enabled" valuePropName="checked" wrapperCol={{ offset: 5, span: 17 }}><Checkbox>二审法院信息</Checkbox></Form.Item>
            {secondCourtEnabled && <><Form.Item label="法院" name="second_court_name"><Select showSearch optionFilterProp="label" options={courtOptions}/></Form.Item><Form.Item label="法庭" name="second_court_courtroom"><Input /></Form.Item><Form.Item label="法官" name="second_court_judge"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(secondCourtName, "法官")} placeholder="请先选择法院" /></Form.Item><Form.Item label="书记员" name="second_court_clerk"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(secondCourtName, "书记员")} placeholder="请先选择法院" /></Form.Item><Form.Item label="案号" name="second_court_case_no"><Input /></Form.Item><Form.Item label="立案日期" name="second_court_filing_date"><DatePicker style={{ width: "100%" }} /></Form.Item><Form.Item label="开庭日期" name="second_court_hearing_date"><DatePicker style={{ width: "100%" }} /></Form.Item></>}
            <Form.Item name="retrial_court_enabled" valuePropName="checked" wrapperCol={{ offset: 5, span: 17 }}><Checkbox>再审法院信息</Checkbox></Form.Item>
            {retrialCourtEnabled && <><Form.Item label="法院" name="retrial_court_name"><Select showSearch optionFilterProp="label" options={courtOptions}/></Form.Item><Form.Item label="法庭" name="retrial_court_courtroom"><Input /></Form.Item><Form.Item label="法官" name="retrial_court_judge"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(retrialCourtName, "法官")} placeholder="请先选择法院" /></Form.Item><Form.Item label="书记员" name="retrial_court_clerk"><Select allowClear showSearch optionFilterProp="label" options={officersForCourt(retrialCourtName, "书记员")} placeholder="请先选择法院" /></Form.Item><Form.Item label="案号" name="retrial_court_case_no"><Input /></Form.Item><Form.Item label="立案日期" name="retrial_court_filing_date"><DatePicker style={{ width: "100%" }} /></Form.Item><Form.Item label="开庭日期" name="retrial_court_hearing_date"><DatePicker style={{ width: "100%" }} /></Form.Item></>}
            <Form.Item label="司法机关备注" name="judicial_remark"><Input.TextArea rows={2} /></Form.Item><Form.Item label="案情说明" name="description"><Input.TextArea rows={3} /></Form.Item>
          </div></div>
        )}
        <div className="case-create-actions">
          <Space>
            {createStep === 0 && <Button type="primary" loading={createSubmitting} onClick={advanceCreateStep}>下一步</Button>}
            {createStep === 1 && (isCounselCreate
              ? <Button type="primary" loading={createSubmitting} onClick={() => void saveLitigants(true)}>完成</Button>
              : <><Button type="primary" loading={createSubmitting} onClick={advanceCreateStep}>下一步</Button>{!isAdministrativeCreate && <Button loading={createSubmitting} onClick={() => void saveLitigants(true)}>完成</Button>}</>)}
            {createStep === 2 && <><Button disabled={createSubmitting} onClick={() => setCreateStep(1)}>上一步</Button><Button type="primary" loading={createSubmitting} onClick={finishCreateFlow}>完成</Button></>}
          </Space>
        </div>
        <Form.Item name="owner" hidden><Input /></Form.Item><Form.Item name="case_type" hidden><Input /></Form.Item>
      </Form>
    </div>
  );
};
