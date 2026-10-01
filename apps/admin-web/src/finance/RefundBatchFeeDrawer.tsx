import { MinusCircleOutlined, PlusOutlined } from "@ant-design/icons";
import { Alert, Button, DatePicker, Drawer, Form, Input, InputNumber, Select, Space, Steps } from "antd";
import type { FormInstance } from "antd";
import type { RefundBatchFeeFormValues } from "./formTypes";
import type { Fee, FinancePersonOption, RefundBatchFeeSubtype, RefundBatchPaymentType } from "./types";

export interface RefundBatchFeeDrawerProps {
  open: boolean;
  kind: "internal" | "ordinary";
  step: number;
  onStepChange: (step: number) => void;
  form: FormInstance<RefundBatchFeeFormValues>;
  baseType: string;
  subTypes: RefundBatchFeeSubtype[];
  paymentTypes: RefundBatchPaymentType[];
  loading: boolean;
  onClose: () => void;
  onSubmit: () => Promise<void>;
  onSyncFirstField: (field: string) => void;
  contracts: Fee[];
  financePeople: FinancePersonOption[];
}

export function RefundBatchFeeDrawer(props: RefundBatchFeeDrawerProps) {
  const { open: refundBatchFeeOpen, kind: refundBatchFeeKind, step: refundBatchFeeStep, onStepChange: setRefundBatchFeeStep, form: refundBatchFeeForm, baseType: refundBatchFeeBaseType, subTypes: refundBatchFeeSubTypes, paymentTypes: refundBatchPaymentTypes, loading: refundBatchFeeLoading, onClose: closeRefundBatchFee, onSubmit: submitRefundBatchFee, onSyncFirstField: syncFirstRefundFeeField, contracts, financePeople } = props;
  return (
      <Drawer
        open={refundBatchFeeOpen}
        title={refundBatchFeeKind === "internal" ? "新增内部费用" : "新增费用"}
        width="min(1000px, 95vw)"
        onClose={closeRefundBatchFee}
        destroyOnHidden
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button onClick={closeRefundBatchFee}>取消</Button>
            {refundBatchFeeStep === 1 && <Button onClick={() => setRefundBatchFeeStep(0)}>上一步</Button>}
            {refundBatchFeeStep === 0 ? (
              <Button type="primary" onClick={async () => {
                await refundBatchFeeForm.validateFields();
                setRefundBatchFeeStep(1);
              }}>下一步</Button>
            ) : (
              <Button type="primary" loading={refundBatchFeeLoading} onClick={() => void submitRefundBatchFee()}>
                {refundBatchFeeBaseType === "代理费" ? "保存费用" : "申请付款"}
              </Button>
            )}
          </div>
        }
      >
        <Steps
          size="small"
          current={refundBatchFeeStep}
          items={[{ title: "新增费用" }, { title: "申请付款" }]}
          style={{ marginBottom: 16 }}
        />
        <Form form={refundBatchFeeForm} layout="vertical">
          <Form.Item name="handler" hidden><Input /></Form.Item>
          {refundBatchFeeStep === 0 ? (
            <>
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 12 }}
              description={
                refundBatchFeeKind === "internal" ? (
                  <>
                    <p style={{ margin: 0 }}>1. 申请付款按照每个案号生成一个申请单。</p>
                    <p style={{ margin: "2px 0 0" }}>2. 点击表格头部（费用类型，基数，实际金额，备注）会把第一行数据同步到各行。</p>
                    <p style={{ margin: "2px 0 0" }}>3. 基数用于计算提成的分母数，点击基数会把第一行数据同步到各行，同时自动计算提成。</p>
                  </>
                ) : (
                  <>
                    <p style={{ margin: 0 }}>1. 同一付款单位可以申请付款，否则请按实际业务进行操作。</p>
                    <p style={{ margin: "2px 0 0" }}>2. 申请付款按照每个合同号生成一个申请单。</p>
                    <p style={{ margin: "2px 0 0" }}>3. 点击表格头部（费用类型，金额，备注，截止日期）会把第一行数据同步到各行。</p>
                    <p style={{ margin: "2px 0 0" }}>4. 截止日期默认为申请之日第5天，如有特殊情况，在申请时自行修改。</p>
                  </>
                )
              }
            />
              <Form.List name="items">
                {(fields, { add, remove }) => (
                  <div className={`finance-refund-batch-fee-table ${refundBatchFeeKind === "internal" ? "is-internal" : "is-ordinary"}`}>
                    <div className="finance-refund-batch-fee-head">
                      {refundBatchFeeKind === "internal" ? (
                        <>
                          <span>案号</span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("fee_type_id")}>费用类型</a></span>
                          <span>支付对象</span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("base_amount")}>基数</a></span>
                          <span>参考提成</span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("amount")}>实际金额</a></span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("remark")}>备注</a></span>
                          <span>操作</span>
                        </>
                      ) : (
                        <>
                          <span>案号</span>
                          <span>合同号</span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("fee_type_id")}>费用类型</a></span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("amount")}>金额</a></span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("remark")}>备注</a></span>
                          <span><a style={{ color: "inherit", cursor: "pointer" }} onClick={() => syncFirstRefundFeeField("deadline")}>截止日期</a></span>
                          <span>操作</span>
                        </>
                      )}
                    </div>
                    {fields.map((field) => {
                      const row = refundBatchFeeForm.getFieldValue(["items", field.name]) || {};
                      const contractOptions = contracts
                        .filter((contract) => contract.customer === row.customer)
                        .map((contract) => ({ value: contract.id, label: contract.serial_no }));
                      return (
                        <div className="finance-refund-batch-fee-row" key={field.key}>
                          <div className="finance-refund-batch-fee-case">
                            <strong>{row.case_no}</strong><small>{row.customer}</small>
                            <Form.Item name={[field.name, "case_id"]} hidden><Input /></Form.Item>
                            <Form.Item name={[field.name, "case_no"]} hidden><Input /></Form.Item>
                            <Form.Item name={[field.name, "customer"]} hidden><Input /></Form.Item>
                          </div>
                          {refundBatchFeeKind === "ordinary" && <Form.Item name={[field.name, "contract_record_id"]} rules={[{ required: true, message: "请选择合同" }]}>
                              <Select showSearch optionFilterProp="label" options={contractOptions} placeholder="请选择" />
                            </Form.Item>}
                          <Form.Item name={[field.name, "fee_type_id"]} rules={[{ required: true, message: "请选择费用类型" }]}>
                            <Select<string | number>
                              showSearch
                              optionFilterProp="label"
                              placeholder="请选择"
                              options={refundBatchFeeSubTypes.length
                                ? refundBatchFeeSubTypes.map((item) => ({ value: item.id, label: item.name }))
                                : [{ value: refundBatchFeeBaseType, label: refundBatchFeeBaseType, disabled: true }]}
                              onChange={(_value, option) => {
                                const selectedOption = Array.isArray(option) ? option[0] : option;
                                refundBatchFeeForm.setFieldValue(
                                  ["items", field.name, "fee_type_name"],
                                  selectedOption?.label || "",
                                );
                              }}
                            />
                          </Form.Item>
                          <Form.Item name={[field.name, "fee_type"]} hidden><Input /></Form.Item>
                          {refundBatchFeeKind === "internal" ? <>
                            <Form.Item name={[field.name, "payee_username"]} rules={[{ required: true, message: "请选择支付对象" }]}>
                              <Select showSearch optionFilterProp="label" options={financePeople.map((person) => ({ value: person.username, label: person.label }))} />
                            </Form.Item>
                            <Form.Item name={[field.name, "base_amount"]} rules={[{ required: true, message: "请输入基数" }]}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
                            <Form.Item name={[field.name, "reference_commission"]} rules={[{ required: true, message: "请输入参考提成" }]}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
                          </> : null}
                          <Form.Item name={[field.name, "amount"]} rules={[{ required: true, message: "请输入金额" }, { validator: (_, value) => value === 0 ? Promise.reject(new Error("金额不能为0")) : Promise.resolve() }]}>
                            <InputNumber precision={2} style={{ width: "100%" }} />
                          </Form.Item>
                          <Form.Item name={[field.name, "remark"]}><Input placeholder="备注" /></Form.Item>
                          {refundBatchFeeKind === "ordinary" && <Form.Item name={[field.name, "deadline"]} rules={[{ required: true, message: "请选择截止日期" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>}
                          <Space size={2}>
                            <Button type="text" aria-label="复制费用行" icon={<PlusOutlined />} onClick={() => add({ ...row, amount: undefined, remark: "" }, field.name + 1)} />
                            <Button type="text" danger aria-label="删除费用行" icon={<MinusCircleOutlined />} disabled={fields.length === 1} onClick={() => remove(field.name)} />
                          </Space>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Form.List>
            </>
          ) : (
            <>
              <Alert type="info" showIcon title={refundBatchFeeBaseType === "代理费" ? "代理费不允许申请付款，本次仅保存费用。" : "同一收款单位可批量申请；系统按每个合同号分别形成付款申请。"} style={{ marginBottom: 12 }} />
              <Form.List name="items">
                {(fields) => <div className="finance-refund-payment-table">
                  <div className="finance-refund-payment-head"><span>案号</span><span>费用类型</span><span>付款金额</span><span>付款备注</span><span>收款单位/支付对象</span></div>
                  {fields.map((field) => {
                    const row = refundBatchFeeForm.getFieldValue(["items", field.name]) || {};
                    const agency = refundBatchFeeBaseType === "代理费";
                    return <div className="finance-refund-payment-row" key={field.key}>
                      <strong>{row.case_no}</strong><span>{row.fee_type_name || row.fee_type}</span>
                      <Form.Item name={[field.name, "payment_amount"]} initialValue={Math.abs(Number(row.amount || 0))} rules={agency ? [] : [{ required: true, message: "请输入付款金额" }]}><InputNumber disabled={agency} min={0.01} precision={2} style={{ width: "100%" }} /></Form.Item>
                      <Form.Item name={[field.name, "payment_remark"]}><Input disabled={agency} /></Form.Item>
                      {refundBatchFeeKind === "internal" ? <Form.Item name={[field.name, "payee_username"]} rules={[{ required: true, message: "请选择支付对象" }]}><Select disabled options={financePeople.map((person) => ({ value: person.username, label: person.label }))} /></Form.Item> : <Form.Item name={[field.name, "payment_type_id"]} rules={agency ? [] : [{ required: true, message: "请选择收款单位" }]}><Select disabled={agency} showSearch optionFilterProp="label" options={refundBatchPaymentTypes.map((item) => ({ value: item.id, label: `${item.payee}｜${item.account_bank}｜${item.account}` }))} /></Form.Item>}
                    </div>;
                  })}
                </div>}
              </Form.List>
            </>
          )}
        </Form>
      </Drawer>
  );
}
