import { Modal, Form, Input, DatePicker, Select, Checkbox } from "antd";
import type { Row, WarehouseCatalogItem } from "./types";

interface CertificateRegisterModalProps {
  open: boolean;
  certificateTarget: Row | null;
  certificateForm: any;
  certificateWarehouseId: number | undefined;
  warehouseCatalog: WarehouseCatalogItem[];
  storageLocationOptions: (warehouseId: number | undefined) => { value: number; label: string }[];
  onOk: () => void;
  onCancel: () => void;
}

export default function CertificateRegisterModal({
  open,
  certificateTarget,
  certificateForm,
  certificateWarehouseId,
  warehouseCatalog,
  storageLocationOptions,
  onOk,
  onCancel,
}: CertificateRegisterModalProps) {
  return (
    <Modal
      open={open}
      title={`登记公证书：${certificateTarget?.serial_no || ""}`}
      okText="保存登记"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={certificateForm} layout="vertical">
        <Form.Item
          label="公证书编号"
          name="certificate_no"
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          label="签发日期"
          name="issued_date"
          rules={[{ required: true }]}
        >
          <DatePicker style={{ width: "100%" }} />
        </Form.Item>
        <div className="form-grid">
          <Form.Item
            label="仓库"
            name="warehouse_id"
            rules={[{ required: true, message: "请选择仓库" }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={warehouseCatalog
                .filter((warehouse) => warehouse.is_active)
                .map((warehouse) => ({
                  value: warehouse.id,
                  label: warehouse.name,
                }))}
              onChange={() =>
                certificateForm.setFieldValue(
                  "storage_location_id",
                  undefined,
                )
              }
            />
          </Form.Item>
          <Form.Item
            label="库位"
            name="storage_location_id"
            rules={[{ required: true, message: "请选择库位" }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={storageLocationOptions(certificateWarehouseId)}
            />
          </Form.Item>
        </div>
        <Form.Item name="physical_received" valuePropName="checked">
          <Checkbox>纸质公证书实物已收到</Checkbox>
        </Form.Item>
        <Form.Item label="登记说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
