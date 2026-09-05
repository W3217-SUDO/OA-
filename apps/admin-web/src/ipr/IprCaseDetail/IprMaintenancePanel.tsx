import { DatePicker,Form,Input,InputNumber,Modal } from "antd";
import type { IprRecord } from "../types";

interface IprMaintenancePanelProps {
  maintenanceTarget: IprRecord | null;
  maintenanceForm: any;
  onClose: () => void;
  onSave: () => void;
}

export function IprMaintenancePanel({
  maintenanceTarget,
  maintenanceForm,
  onClose,
  onSave,
}: IprMaintenancePanelProps) {
  return (
    <Modal
      open={!!maintenanceTarget}
      title={
        maintenanceTarget
          ? `维护知识产权案件：${maintenanceTarget.serial_no}`
          : "维护知识产权案件"
      }
      onCancel={onClose}
      onOk={onSave}
      okText="保存维护"
    >
      <Form form={maintenanceForm} layout="vertical">
        <Form.Item name="deadline" label="办理期限">
          <DatePicker style={{ width: "100%" }} />
        </Form.Item>
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
        <Form.Item name="comment" label="维护说明">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
