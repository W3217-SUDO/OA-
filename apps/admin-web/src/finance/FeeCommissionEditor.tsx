import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, InputNumber, Modal, Radio, Select, Space, Table } from "antd";
import type { FormInstance } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";

type NamePrefix = Array<string | number>;
type PersonOption = { value: string; label: string };
type CommissionPreviewItem = {
  preview_key: string;
  employee_username: string;
  employee_display_name?: string;
  commission_type?: string;
  commission_role?: string;
  base_amount?: number;
  rate?: number;
  fixed_amount?: number;
  actual_amount?: number;
  calculation_source?: string;
  scheme_id?: number;
  scheme_start_date?: string;
  scheme_end_date?: string;
};
type CommissionPreview = { items: CommissionPreviewItem[]; missing_messages: string[] };

export interface FeeCommissionEditorProps {
  form: FormInstance;
  isAgencyFee: boolean;
  people: PersonOption[];
  /** Absolute form path for watches and FormInstance reads/writes. */
  watchPrefix?: NamePrefix;
  /** Relative form path for fields rendered inside a parent Form.List. */
  fieldPrefix?: NamePrefix;
  caseId?: number;
  className?: string;
}

const fieldName = (prefix: NamePrefix, name: string) => [...prefix, name];

export function FeeCommissionEditor({
  form,
  isAgencyFee,
  people,
  watchPrefix = [],
  fieldPrefix = [],
  caseId,
  className = "finance-fee-commission-details",
}: FeeCommissionEditorProps) {
  const watchPrefixKey = watchPrefix.join(".");
  const fieldPrefixKey = fieldPrefix.join(".");
  const modeWatchName = useMemo(() => fieldName(watchPrefix, "commission_mode"), [watchPrefixKey]);
  const detailsWatchName = useMemo(() => fieldName(watchPrefix, "commission_details"), [watchPrefixKey]);
  const caseIdWatchName = useMemo(() => fieldName(watchPrefix, "case_record_id"), [watchPrefixKey]);
  const amountWatchName = useMemo(() => fieldName(watchPrefix, "amount"), [watchPrefixKey]);
  const modeFieldName = useMemo(() => fieldName(fieldPrefix, "commission_mode"), [fieldPrefixKey]);
  const detailsFieldName = useMemo(() => fieldName(fieldPrefix, "commission_details"), [fieldPrefixKey]);
  const commissionMode = Form.useWatch(modeWatchName, form);
  const watchedCaseRecordId = Number(Form.useWatch(caseIdWatchName, { form, preserve: true }) || 0);
  const caseRecordId = Number(caseId ?? watchedCaseRecordId ?? 0);
  const amount = Number(Form.useWatch(amountWatchName, form) || 0);
  const commissionDetails = Form.useWatch(detailsWatchName, form) || [];
  const [preview, setPreview] = useState<CommissionPreview | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const requestRef = useRef(0);

  const mode = commissionMode === "manual" ? "manual" : "automatic";
  const isCaseLayout = className.includes("case-fee");
  const manualHeaderClass = isCaseLayout ? "case-fee-commission-header" : "finance-fee-commission-header";
  const manualRowClass = isCaseLayout ? "case-fee-commission-row" : "finance-fee-commission-row";
  const manualTotalClass = "finance-fee-commission-total";
  const switchToAutomatic = () => {
    requestRef.current += 1;
    setPreview(null);
    setPreviewError("");
    form.setFieldValue(detailsWatchName, []);
    form.setFieldValue(modeWatchName, "automatic");
  };

  useEffect(() => {
    if (isAgencyFee && commissionMode !== "automatic" && commissionMode !== "manual") {
      form.setFieldValue(modeWatchName, "automatic");
    }
  }, [commissionMode, form, isAgencyFee, modeWatchName]);

  useEffect(() => {
    if (!isAgencyFee && form.getFieldValue(modeWatchName) === "automatic") {
      form.setFieldValue(modeWatchName, undefined);
      form.setFieldValue(detailsWatchName, []);
    }
  }, [detailsWatchName, form, isAgencyFee, modeWatchName]);

  useEffect(() => {
    const requestId = ++requestRef.current;
    if (!isAgencyFee || mode !== "automatic" || !Number.isInteger(caseRecordId) || caseRecordId <= 0 || amount <= 0) {
      setPreview(null);
      setPreviewError("");
      setPreviewLoading(false);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setPreviewLoading(true);
      setPreviewError("");
      try {
        const { data } = await api.post(`/cases/${caseRecordId}/commission-preview`, { amount }, { signal: controller.signal });
        const currentCaseId = Number(caseId ?? form.getFieldValue(caseIdWatchName) ?? 0);
        const currentAmount = Number(form.getFieldValue(amountWatchName) || 0);
        if (requestRef.current !== requestId || form.getFieldValue(modeWatchName) !== "automatic" || currentCaseId !== caseRecordId || currentAmount !== amount) return;
        const nextPreview: CommissionPreview = {
          items: Array.isArray(data?.items) ? data.items : [],
          missing_messages: Array.isArray(data?.missing_messages) ? data.missing_messages : [],
        };
        setPreview(nextPreview);
        form.setFieldValue(detailsWatchName, nextPreview.items.map((item) => ({
          preview_key: item.preview_key,
          employee_username: item.employee_username,
          employee_display_name: item.employee_display_name,
          commission_type: item.commission_type,
          commission_role: item.commission_role,
          base_amount: item.base_amount,
          rate: item.rate,
          fixed_amount: item.fixed_amount,
          actual_amount: item.actual_amount,
          amount: item.actual_amount,
          calculation_source: item.calculation_source,
          scheme_id: item.scheme_id,
          scheme_start_date: item.scheme_start_date,
          scheme_end_date: item.scheme_end_date,
        })));
      }
      catch (error: any) {
        if (controller.signal.aborted || requestRef.current !== requestId) return;
        setPreview(null);
        setPreviewError(error?.response?.data?.detail || "提成预览加载失败");
      }
      finally {
        if (requestRef.current === requestId) setPreviewLoading(false);
      }
    }, 350);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [amount, amountWatchName, caseIdWatchName, caseRecordId, detailsWatchName, form, isAgencyFee, mode, modeWatchName]);

  if (!isAgencyFee) return null;

  return (
    <section className={className}>
      <Form.Item name={modeFieldName} hidden />
      <Form.Item name={detailsFieldName} hidden />
      <Space size="middle" wrap>
        <strong>员工提成</strong>
        <Radio.Group
          value={mode}
          onChange={(event) => {
            const nextMode = event.target.value as "automatic" | "manual";
            if (nextMode === "manual") {
              requestRef.current += 1;
              form.setFieldValue(modeWatchName, "manual");
              return;
            }
            if (mode === "manual" && commissionDetails.length) {
              Modal.confirm({
                title: "切换为自动计算",
                content: "切换后将按方案重新计算当前草稿提成。",
                okText: "确认切换",
                cancelText: "取消",
                onOk: switchToAutomatic,
              });
              return;
            }
            switchToAutomatic();
          }}
          options={[
            { value: "automatic", label: "自动计算" },
            { value: "manual", label: "手动录入" },
          ]}
        />
      </Space>
      {mode === "automatic" ? <>
        {(!caseRecordId || amount <= 0) && <div style={{ margin: "8px 0" }}>填写关联案件和金额后生成预览</div>}
        {previewLoading && <Alert type="info" showIcon message="正在更新提成预览" style={{ marginBottom: 12 }} />}
        {previewError && <Alert type="error" showIcon message={previewError} style={{ marginBottom: 12 }} />}
        {preview?.missing_messages.map((item) => <Alert key={item} type="warning" showIcon message={item} style={{ marginBottom: 8 }} />)}
        {preview?.items.length ? <Table<CommissionPreviewItem>
          rowKey="preview_key"
          size="small"
          pagination={false}
          scroll={{ x: 760 }}
          dataSource={preview.items}
          columns={[
            { title: "员工", width: 130, render: (_, item) => item.employee_display_name || item.employee_username || "员工待维护" },
            { title: "角色", width: 110, render: (_, item) => item.commission_role || item.commission_type || "提成" },
            { title: "方案", width: 170, render: (_, item) => item.scheme_id == null ? "—" : `${item.scheme_id}${item.scheme_start_date || item.scheme_end_date ? ` (${item.scheme_start_date || "—"} 至 ${item.scheme_end_date || "—"})` : ""}` },
            { title: "计算", width: 130, render: (_, item) => item.fixed_amount != null && Number(item.fixed_amount) !== 0 ? `固定金额 ${Number(item.fixed_amount).toFixed(2)}` : item.rate != null ? `比例 ${(Number(item.rate) * 100).toFixed(2)}%` : "—" },
            { title: "金额", width: 110, align: "right", render: (_, item) => Number(item.actual_amount || 0).toFixed(2) },
          ]}
        /> : null}
      </> : <Form.List name={detailsFieldName}>
        {(fields, { add, remove }) => <>
          <div className={manualHeaderClass}>
            <strong>手动提成明细</strong>
            <Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ commission_type: "员工提成", amount: undefined, remark: "" })}>新建员工提成</Button>
          </div>
          {fields.map((field) => <div className={manualRowClass} key={field.key}>
            <Form.Item {...field} name={[field.name, "employee_username"]} label="员工" rules={[{ required: true, message: "请选择员工" }]}><Select showSearch optionFilterProp="label" options={people} /></Form.Item>
            <Form.Item {...field} name={[field.name, "commission_type"]} label="提成类型" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item {...field} name={[field.name, "amount"]} label="提成金额" rules={[{ required: true, message: "请输入提成金额" }]}><InputNumber min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item>
            <Form.Item {...field} name={[field.name, "remark"]} label="备注"><Input /></Form.Item>
            <Button danger type="text" aria-label="删除员工提成" icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
          </div>)}
          {commissionDetails.length > 0 && <div className={manualTotalClass}>已分配员工提成：{commissionDetails.reduce((sum: number, detail: Record<string, any>) => sum + Number(detail?.amount || 0), 0).toFixed(2)}</div>}
        </>}
      </Form.List>}
    </section>
  );
}
