import {
Button,
DatePicker,
Form,
Input,
InputNumber,
Modal,
Select,
Space,
} from "antd";
import type { Customer,IprRecord } from "./types";

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
  onOpenDeadlineOffset: () => void;
  onCloseDeadlineOffset: () => void;
  onApplyDeadlineOffset: () => void;
}

export function IprCaseCreateModal({
  open,
  editing,
  form,
  customers,
  deadlineOffsetOpen,
  deadlineOffsetForm,
  kind,
  onClose,
  onCreate,
  onOpenDeadlineOffset,
  onCloseDeadlineOffset,
  onApplyDeadlineOffset,
}: IprCaseCreateModalProps) {
  return (
    <>
      <Modal
        open={open}
        title={
          editing
            ? `编辑知识产权案件草稿：${editing.serial_no}`
            : "新建知识产权案件草稿"
        }
        width={760}
        onCancel={onClose}
        onOk={onCreate}
        okText={editing ? "保存修改" : "保存草稿"}
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
            <Form.Item
              name="title"
              label="案件名称"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item name="application_no" label="申请号/注册号">
              <Input />
            </Form.Item>
            <Form.Item name="application_type" label="申请类型">
              <Input placeholder="如发明、实用新型、外观设计、注册商标" />
            </Form.Item>
            <Form.Item name="applicant" label="申请人/权利人">
              <Input />
            </Form.Item>
            <Form.Item name="case_manager" label="案件负责人">
              <Input />
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
            <Form.Item name="deadline" label="办理期限">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Button
              type="link"
              onClick={onOpenDeadlineOffset}
            >
              按基准日计算截止日期
            </Button>
          </div>
          <div className="form-grid">
            <Form.Item name="annual_fee_year" label="年费年度">
              <InputNumber min={1} max={100} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="rate" label="费率">
              <InputNumber
                min={0}
                max={1}
                step={0.01}
                style={{ width: "100%" }}
              />
            </Form.Item>
          </div>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={3} />
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
