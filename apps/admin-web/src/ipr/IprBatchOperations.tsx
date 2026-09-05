import { Alert,Button,Card,DatePicker,Descriptions,Form,Input,InputNumber,Modal,Select } from "antd";
import dayjs from "dayjs";
import type { Customer,IprBatchCreateError,IprFileType,IprRecord } from "./types";

interface IprBatchOperationsProps {
  // 批量创建
  iprBatchCreateOpen: boolean;
  iprBatchCreateForm: any;
  iprBatchCreateErrors: IprBatchCreateError[];
  customers: Customer[];
  onCloseBatchCreate: () => void;
  onCreateBatch: () => void;

  // 批量上传文档
  iprBatchOpen: boolean;
  iprBatchForm: any;
  iprBatchFile: File | null;
  items: IprRecord[];
  batchSelectedKinds: string[];
  batchAvailableFileTypes: IprFileType[];
  iprFileTypes: IprFileType[];
  onCloseBatchUpload: () => void;
  onUploadBatchFile: () => void;
  onBatchFileChange: (file: File | null) => void;

  // 批量维护
  iprMaintenanceOpen: boolean;
  iprMaintenanceForm: any;
  selectedIprCaseIds: number[];
  onCloseBatchMaintenance: () => void;
  onSaveBatchMaintenance: () => void;

  // 案件重提
  iprRebootOpen: boolean;
  iprRebootForm: any;
  iprRebootPreview: {
    source_case_id: number;
    source_case_no: string;
    source_title: string;
    source_status: string;
    next_serial_no: string;
  } | null;
  onCloseReboot: () => void;
  onCreateReboot: () => void;
}

export function IprBatchOperations({
  iprBatchCreateOpen,
  iprBatchCreateForm,
  iprBatchCreateErrors,
  customers,
  onCloseBatchCreate,
  onCreateBatch,
  iprBatchOpen,
  iprBatchForm,
  iprBatchFile,
  items,
  batchSelectedKinds,
  batchAvailableFileTypes,
  onCloseBatchUpload,
  onUploadBatchFile,
  onBatchFileChange,
  iprMaintenanceOpen,
  iprMaintenanceForm,
  selectedIprCaseIds,
  onCloseBatchMaintenance,
  onSaveBatchMaintenance,
  iprRebootOpen,
  iprRebootForm,
  iprRebootPreview,
  onCloseReboot,
  onCreateReboot,
}: IprBatchOperationsProps) {
  return (
    <>
      <Modal
        open={iprBatchCreateOpen}
        title="批量新建知识产权案件"
        width={1120}
        onCancel={onCloseBatchCreate}
        onOk={onCreateBatch}
        okText="提交创建"
      >
        <Alert
          type="info"
          showIcon
          message="与旧系统一致：先选择客户，再逐行填写案件类型、案件阶段、立案日期和处理期限。"
          description="系统先校验全部行；有效行会在同一事务内创建，错误行不会落库，并在下方按行提示。"
          style={{ marginBottom: 16 }}
        />
        {iprBatchCreateErrors.length ? (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message="以下行未创建"
            description={
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {iprBatchCreateErrors.map((item) => (
                  <li key={item.row_no}>
                    第 {item.row_no} 行：{item.message}
                  </li>
                ))}
              </ul>
            }
          />
        ) : null}
        <Form form={iprBatchCreateForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              name="customer"
              label="客户"
              rules={[{ required: true, message: "请选择客户" }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                options={customers.map((row) => ({
                  value: row.title,
                  label: `${row.title}（${row.serial_no}）`,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="case_kind"
              label="案件类别"
              rules={[{ required: true }]}
            >
              <Select
                options={["专利", "商标"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
          </div>
          <Form.List
            name="rows"
            rules={[
              {
                validator: async (_, rows) => {
                  if (!rows?.length)
                    throw new Error("请至少新增一行案件");
                },
              },
            ]}
          >
            {(fields, { add, remove }) => (
              <>
                {fields.map((field, index) => (
                  <Card
                    key={field.key}
                    size="small"
                    title={`第 ${index + 1} 行`}
                    style={{ marginBottom: 12 }}
                    extra={
                      <Button
                        danger
                        type="link"
                        disabled={fields.length === 1}
                        onClick={() => remove(field.name)}
                      >
                        移除
                      </Button>
                    }
                  >
                    <div className="form-grid">
                      <Form.Item
                        {...field}
                        name={[field.name, "case_type"]}
                        label="案件类型"
                        rules={[
                          { required: true, message: "请输入案件类型" },
                        ]}
                      >
                        <Input placeholder="如发明专利申请、商标注册" />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, "case_phase"]}
                        label="案件阶段"
                        rules={[
                          { required: true, message: "请输入案件阶段" },
                        ]}
                      >
                        <Input placeholder="如申请阶段" />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, "case_register_date"]}
                        label="立案日期"
                        rules={[
                          { required: true, message: "请选择立案日期" },
                        ]}
                      >
                        <DatePicker style={{ width: "100%" }} />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, "deadline"]}
                        label="处理期限"
                        rules={[
                          { required: true, message: "请选择处理期限" },
                        ]}
                      >
                        <DatePicker style={{ width: "100%" }} />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, "title"]}
                        label="案件名称"
                      >
                        <Input placeholder="未填写时按案件类型生成" />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, "application_no"]}
                        label="申请号/注册号"
                      >
                        <Input />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, "application_type"]}
                        label="申请类型"
                      >
                        <Input />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, "applicant"]}
                        label="申请人/权利人"
                      >
                        <Input />
                      </Form.Item>
                    </div>
                    <Form.Item
                      {...field}
                      name={[field.name, "description"]}
                      label="说明"
                    >
                      <Input.TextArea rows={2} maxLength={2000} />
                    </Form.Item>
                  </Card>
                ))}
                <Button
                  onClick={() =>
                    add({
                      case_register_date: dayjs(),
                      deadline: dayjs().add(30, "day"),
                    })
                  }
                >
                  新增一行
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      <Modal
        open={iprRebootOpen}
        title="知识产权案件重提"
        onCancel={onCloseReboot}
        onOk={onCreateReboot}
        okText="确认重提"
      >
        {iprRebootPreview ? (
          <>
            <Descriptions bordered size="small" column={1} items={[
              { key: "source", label: "原案件", children: `${iprRebootPreview.source_case_no}｜${iprRebootPreview.source_title}` },
              { key: "status", label: "原案件状态", children: iprRebootPreview.source_status },
              { key: "target", label: "新案件编号", children: iprRebootPreview.next_serial_no },
            ]} />
            <Alert
              type="info"
              showIcon
              style={{ marginTop: 16 }}
              message="重提会复制业务信息和客户、联系人、协作律所关联，原案件不会被覆盖。新旧案件均会写入可追溯的审计事件。"
            />
            <Form form={iprRebootForm} layout="vertical" style={{ marginTop: 16 }}>
              <Form.Item name="reason" label="重提说明">
                <Input.TextArea rows={3} maxLength={1000} />
              </Form.Item>
            </Form>
          </>
        ) : null}
      </Modal>

      <Modal
        open={iprBatchOpen}
        title="批量上传知识产权案件文档"
        onCancel={onCloseBatchUpload}
        onOk={onUploadBatchFile}
        okText="批量上传"
      >
        <Form form={iprBatchForm} layout="vertical">
          <Form.Item
            name="case_ids"
            label="目标案件"
            rules={[{ required: true, message: "请选择至少一个在办案件" }]}
          >
            <Select
              mode="multiple"
              options={items
                .filter((item) => item.status === "在办")
                .map((item) => ({
                  value: item.id,
                  label: `${item.serial_no}｜${item.title}`,
                }))}
            />
          </Form.Item>
          {batchSelectedKinds.length > 1 && (
            <div
              style={{
                marginTop: -14,
                marginBottom: 12,
                color: "#666",
              }}
            >
              已选择{batchSelectedKinds.join("、")}
              案件，仅显示同时适用的文档类型。
            </div>
          )}
          <Form.Item
            name="category"
            label="文档类型"
            rules={[{ required: true }]}
          >
            <Select
              notFoundContent={
                iprBatchForm.getFieldValue?.("case_ids")?.length
                  ? "没有同时适用于所选案件的文档类型"
                  : "请先选择目标案件"
              }
              options={batchAvailableFileTypes.map((item) => ({
                value: item.name,
                label: `${item.name}${
                  item.requires_transmission ? "（待转文）" : ""
                }`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="document_date"
            label="文档日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="案件文档" required>
            <input
              type="file"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar"
              onChange={(event) =>
                onBatchFileChange(event.target.files?.[0] || null)
              }
            />
            {iprBatchFile && <div>{iprBatchFile.name}</div>}
          </Form.Item>
          <Form.Item name="remark" label="说明">
            <Input.TextArea rows={2} maxLength={1000} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={iprMaintenanceOpen}
        title={`批量维护知识产权案件（已选 ${selectedIprCaseIds.length} 件）`}
        onCancel={onCloseBatchMaintenance}
        onOk={onSaveBatchMaintenance}
        okText="确认维护"
      >
        <p style={{ color: "#666" }}>
          仅会更新填写的字段；系统会在写入前校验全部目标案件均为当前账号可维护的在办案件，任一案件不符合时不会修改任何案件。
        </p>
        <Form form={iprMaintenanceForm} layout="vertical">
          <Form.Item name="case_manager" label="案件经办人">
            <Input placeholder="填写有效系统用户名" />
          </Form.Item>
          <Form.Item name="deadline" label="办理期限">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="annual_fee_year" label="首年缴费年度">
            <InputNumber min={1} max={100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="rate" label="减缓比例">
            <InputNumber
              min={0}
              max={1}
              step={0.01}
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Form.Item name="comment" label="维护说明">
            <Input.TextArea rows={2} maxLength={1000} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
