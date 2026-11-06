import { POPUP_WIDTH } from "../components/common/popupSize";
import { KeywordPersonSelect } from "../components/KeywordPersonSelect";
import {
Button,
Checkbox,
Collapse,
DatePicker,
Form,
Input,
InputNumber,
Modal,
Select,
Space,
} from "antd";
import type { Customer,IprRecord } from "./types";
import { IprApplicantSelect } from "./IprApplicantSelect";
import { IprApplicationTypeSelect, IprPhaseSelect } from "./IprApplicationTypeSelect";

interface IprCaseCreateModalProps {
  open: boolean;
  editing: IprRecord | null;
  form: any;
  customers: Customer[];
  deadlineOffsetOpen: boolean;
  deadlineOffsetForm: any;
  kind: string;
  onClose: () => void;
  onCreate: () => void;
  /** 501614：保存后清空，接着新建下一件。 */
  onCreateAndNew?: () => void;
  peopleOptions?: { value: string; label: string }[];
  onOpenDeadlineOffset: () => void;
  onCloseDeadlineOffset: () => void;
  onApplyDeadlineOffset: () => void;
}

// 501614（fwl 11-05）：专利非诉案件的新建、编辑按旧系统“案件新建”弹窗：必填、选填、勾选项和按钮都照旧系统。
const PATENT_FLAGS: [string, string][] = [["has_priority", "优先权"], ["has_foreign", "涉外案件"], ["has_relief", "费用减缓"], ["has_advanced", "提前公开"],
  ["has_request_view", "提前实审"], ["has_private_inventor", "不公发明人"], ["has_iu", "一发一实"]];
const COST_SLOW_OPTIONS = [{ value: "1.00", label: "无减缓" }, { value: "0.85", label: "减缓85%" }, { value: "0.70", label: "减缓70%" }];
const FIRST_YEAR_OPTIONS = Array.from({ length: 20 }, (_, index) => ({ value: index + 1, label: `第${index + 1}年` }));

export function IprCaseCreateModal({ open, editing, form, customers, deadlineOffsetOpen, deadlineOffsetForm, onClose, onCreate, onCreateAndNew, peopleOptions = [], onOpenDeadlineOffset, onCloseDeadlineOffset, onApplyDeadlineOffset }: IprCaseCreateModalProps) {
  const person = (name: string, label: string, required: boolean, placeholder = "输入姓名或账号搜索") => (
    <Form.Item name={name} label={label} rules={required ? [{ required: true, message: `请选择${label}` }] : undefined}>
      <KeywordPersonSelect allowClear options={peopleOptions} placeholder={placeholder} />
    </Form.Item>
  );
  return (
    <>
      <Modal
        open={open}
        title={
          editing
            ? `编辑知识产权案件草稿：${editing.serial_no}`
            : "新建知识产权案件草稿"
        }
        width={POPUP_WIDTH.md}
        onCancel={onClose}
        footer={[
          <Button key="close" onClick={onClose}>关闭</Button>,
          ...(!editing && onCreateAndNew ? [<Button key="new" onClick={onCreateAndNew}>保存并新建</Button>] : []),
          <Button key="save" type="primary" onClick={onCreate}>{editing ? "保存修改" : "保存"}</Button>,
        ]}
      >
        <Form form={form} layout="vertical">
          <div className="form-grid">
            <Form.Item
              name="case_kind"
              label="案件类型"
              rules={[{ required: true }]}
            >
              <Select
                disabled={!!editing}
                options={["专利", "商标"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="case_category"
              label="案件属性"
              rules={[{ required: true }]}
            >
              <Select
                options={[
                  { value: "non_litigation", label: "非诉案件" },
                  { value: "litigation", label: "诉讼案件" },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="customer"
              label="客户"
              rules={[{ required: true }]}
            >
              <Select
                disabled={!!editing}
                showSearch
                optionFilterProp="label"
                options={customers.map((row) => ({
                  value: row.title,
                  label: `${row.title}（${row.serial_no}）`,
                }))}
              />
            </Form.Item>
            <Form.Item name="contract_record_id" hidden>
              <InputNumber />
            </Form.Item>
            <Form.Item noStyle shouldUpdate={(prev, next) => prev.contract_no !== next.contract_no}>
              {({ getFieldValue }) => getFieldValue("contract_no") ? (
                <Form.Item name="contract_no" label="关联合同">
                  <Input disabled />
                </Form.Item>
              ) : null}
            </Form.Item>
            <Form.Item noStyle shouldUpdate={(previous, current) => previous.case_kind !== current.case_kind || previous.case_category !== current.case_category}>
              {({ getFieldValue }) => getFieldValue("case_kind") === "专利" && getFieldValue("case_category") !== "litigation" ? (
                <Form.Item name="title" label="专利名称" rules={[{ required: true, message: "请输入专利名称" },
                  { pattern: /^\S+$/, message: "专利名称不允许有空格" }]}>
                  <Input placeholder="专利案件名不允许有空格" />
                </Form.Item>
              ) : (
                <Form.Item name="title" label="案件名称" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
              )}
            </Form.Item>
            <Form.Item name="application_no" label="申请号/注册号">
              <Input />
            </Form.Item>
            <Form.Item noStyle shouldUpdate={(previous, current) => previous.case_kind !== current.case_kind}>
              {({ getFieldValue }) => (
                <Form.Item name="application_type" label="申请类型" rules={[{ required: true, message: "请选择申请类型" }]}>
                  <IprApplicationTypeSelect caseKind={getFieldValue("case_kind")} />
                </Form.Item>
              )}
            </Form.Item>
            {/* 501612：案件阶段照旧系统，跟着申请类型给选项，默认“申请立案”。 */}
            <Form.Item noStyle shouldUpdate={(previous, current) => previous.application_type !== current.application_type}>
              {({ getFieldValue }) => (
                <Form.Item name="case_phase" label="案件阶段" rules={[{ required: true, message: "请选择案件阶段" }]}>
                  <IprPhaseSelect applicationType={getFieldValue("application_type")} />
                </Form.Item>
              )}
            </Form.Item>
            <Form.Item noStyle shouldUpdate={(previous, current) => previous.case_kind !== current.case_kind || previous.case_category !== current.case_category}>
              {({ getFieldValue }) => getFieldValue("case_kind") === "专利" && getFieldValue("case_category") !== "litigation" ? (
                <>
                  {person("agent", "代理人", true)}
                  {person("writer", "撰稿人", true)}
                  <Form.Item name="card_no" label="证件号码" rules={[{ required: true, message: "请输入证件号码" },
                    { pattern: /^[0-9A-Za-z]+$/, message: "证件号码不允许有空格及特殊字符" }]}>
                    <Input placeholder="不允许有空格及特殊字符" />
                  </Form.Item>
                  <Form.Item name="applicant" label="申请人" rules={[{ required: true, message: "请填写申请人" }]}>
                    <IprApplicantSelect />
                  </Form.Item>
                  <Form.Item name="inventor" label="发明人" rules={[{ required: true, message: "请填写发明人" }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="authorization_date" label="授权日">
                    <DatePicker style={{ width: "100%" }} />
                  </Form.Item>
                  <Form.Item name="source_date" label="案源日">
                    <DatePicker style={{ width: "100%" }} />
                  </Form.Item>
                  {person("case_source", "案源人", false, "默认本人")}
                  <Form.Item name="ref_case_no" label="关联案号">
                    <Input />
                  </Form.Item>
                  <Form.Item name="first_annual_year" label="首年年费年度">
                    <Select allowClear placeholder="请选择" options={FIRST_YEAR_OPTIONS} />
                  </Form.Item>
                  <Form.Item name="cost_slow_rate" label="费用减缓比例">
                    <Select options={COST_SLOW_OPTIONS} />
                  </Form.Item>
                  {person("case_manager", "案件管理人", false, "默认本人")}
                  <div className="ipr-patent-flags" style={{ gridColumn: "1 / -1", display: "flex", flexWrap: "wrap", gap: "4px 16px", marginBottom: 12 }}>
                    {PATENT_FLAGS.map(([name, label]) => (
                      <Form.Item key={name} name={name} valuePropName="checked" noStyle>
                        <Checkbox>{label}</Checkbox>
                      </Form.Item>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <Form.Item name="applicant" label="申请人/权利人">
                    <IprApplicantSelect asText />
                  </Form.Item>
                  <Form.Item name="case_manager" label="案件管理人">
                    <Input />
                  </Form.Item>
                </>
              )}
            </Form.Item>
            <Form.Item
              noStyle
              shouldUpdate={(previous, current) =>
                previous.case_category !== current.case_category
              }
            >
              {({ getFieldValue }) =>
                getFieldValue("case_category") === "litigation" ? (
                  <>
                    <Form.Item name="court_case_no" label="法院案号">
                      <Input />
                    </Form.Item>
                    <Form.Item name="court_name" label="受理法院">
                      <Input />
                    </Form.Item>
                    <Form.Item name="judge" label="承办法官">
                      <Input />
                    </Form.Item>
                    <Form.Item name="clerk" label="书记员">
                      <Input />
                    </Form.Item>
                    <Form.Item name="plaintiff" label="原告">
                      <Input />
                    </Form.Item>
                    <Form.Item name="defendant" label="被告">
                      <Input />
                    </Form.Item>
                    <Form.Item name="third_parties" label="第三人">
                      <Input />
                    </Form.Item>
                  </>
                ) : null
              }
            </Form.Item>
            <Form.Item name="application_date" label="申请日期">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item noStyle shouldUpdate={(previous, current) => previous.case_kind !== current.case_kind || previous.case_category !== current.case_category}>
            {({ getFieldValue }) => {
              const patent = getFieldValue("case_kind") === "专利" && getFieldValue("case_category") !== "litigation";
              const deadlineFields = <>
                <div className="form-grid">
                  <Form.Item name="deadline" label="办理期限">
                    <DatePicker style={{ width: "100%" }} />
                  </Form.Item>
                  <Button type="link" onClick={onOpenDeadlineOffset}>按基准日计算截止日期</Button>
                </div>
                <Form.Item name="description" label="说明">
                  <Input.TextArea rows={3} />
                </Form.Item>
              </>;
              // 501614：办理期限、说明旧系统新建弹窗里没有，专利非诉案件收进“更多”。
              return patent
                ? <Collapse ghost size="small" items={[{ key: "more", label: "更多（办理期限、说明）", children: deadlineFields, forceRender: true }]} />
                : deadlineFields;
            }}
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={deadlineOffsetOpen}
        title="案件截止日期设定"
        onCancel={onCloseDeadlineOffset}
        onOk={onApplyDeadlineOffset}
        okText="确定"
      >
        <Form form={deadlineOffsetForm} layout="vertical">
          <Form.Item
            name="base_date"
            label="基准日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Space.Compact block>
            <Form.Item
              name="years"
              label="年"
              initialValue={0}
              style={{ flex: 1 }}
            >
              <InputNumber style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              name="months"
              label="月"
              initialValue={0}
              style={{ flex: 1 }}
            >
              <InputNumber style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              name="days"
              label="日"
              initialValue={0}
              style={{ flex: 1 }}
            >
              <InputNumber style={{ width: "100%" }} />
            </Form.Item>
          </Space.Compact>
        </Form>
      </Modal>
    </>
  );
}
