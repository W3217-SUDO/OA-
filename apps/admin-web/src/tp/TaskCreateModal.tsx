import {
  Button,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Upload,
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import type { UploadFile } from "antd";
import type { FormInstance } from "antd";
import dayjs from "dayjs";
import type { PeopleOption } from "./types";

export interface TaskCreateModalProps {
  open: boolean;
  createForm: FormInstance;
  peopleOptions: PeopleOption[];
  createMaterialFiles: UploadFile[];
  actionSubmitting: boolean;
  onCancel: () => void;
  onOk: () => void;
  onMaterialFilesChange: {
    beforeUpload: (file: UploadFile) => boolean;
    onRemove: (file: UploadFile) => void;
  };
}

export default function TaskCreateModal(props: TaskCreateModalProps) {
  const {
    open,
    createForm,
    peopleOptions,
    createMaterialFiles,
    actionSubmitting,
    onCancel,
    onOk,
    onMaterialFilesChange,
  } = props;

  return (
    <Modal
      open={open}
      title="新增任务"
      okText="发起任务"
      cancelText="取消"
      confirmLoading={actionSubmitting}
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={createForm} layout="vertical">
        <Form.Item label="任务内容" name="title" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <div className="form-grid">
          <Form.Item label="负责人" name="owner" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="请选择系统员工"
              options={peopleOptions.map((item) => ({
                value: item.username,
                label: item.label,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="开始时间"
            name="start_at"
            rules={[{ required: true, message: "请选择开始时间" }]}
          >
            <DatePicker
              showTime={{ format: "HH:mm" }}
              format="YYYY-MM-DD HH:mm"
              style={{ width: "100%" }}
              disabledDate={(date) =>
                date.isBefore(dayjs(), "day") ||
                date.isAfter(dayjs().add(30, "day"), "day")
              }
            />
          </Form.Item>
          <Form.Item
            label="结束时间"
            name="end_at"
            rules={[{ required: true, message: "请选择结束时间" }]}
          >
            <DatePicker
              showTime={{ format: "HH:mm" }}
              format="YYYY-MM-DD HH:mm"
              style={{ width: "100%" }}
              disabledDate={(date) =>
                date.isBefore(dayjs(), "day") ||
                date.isAfter(dayjs().add(30, "day"), "day")
              }
            />
          </Form.Item>
          <Form.Item label="优先级" name="priority">
            <Select
              options={["普通", "重要", "紧急"].map((value) => ({
                value,
                label: value,
              }))}
            />
          </Form.Item>
          <Form.Item label="任务来源" name="source">
            <Select
              options={[
                "自动",
                "人工",
                "案件任务",
                "合同任务",
                "客户任务",
                "公证书交接任务",
              ].map((value) => ({ value, label: value }))}
            />
          </Form.Item>
        </div>
        <Form.Item label="协作人" name="collaborators">
          <Select
            mode="multiple"
            showSearch
            optionFilterProp="label"
            placeholder="请选择系统员工，可添加多人"
            options={peopleOptions.map((item) => ({
              value: item.username,
              label: item.label,
            }))}
          />
        </Form.Item>
        <Form.Item label="关联案件" name="case_nos">
          <Select
            mode="tags"
            tokenSeparators={[",", "，", ";", "；"]}
            placeholder="输入案号后回车，可关联多个案件"
          />
        </Form.Item>
        <Form.Item label="客户" name="customer">
          <Input />
        </Form.Item>
        <Form.Item label="任务说明" name="description">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item label="任务资料附件（可多选，单个不超过 20MB）">
          <Upload
            multiple
            fileList={createMaterialFiles}
            beforeUpload={onMaterialFilesChange.beforeUpload}
            onRemove={onMaterialFilesChange.onRemove}
          >
            <Button icon={<UploadOutlined />}>选择任务资料附件</Button>
          </Upload>
        </Form.Item>
      </Form>
    </Modal>
  );
}
