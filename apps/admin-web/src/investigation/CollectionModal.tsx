import { Modal, Form, AutoComplete, Input, DatePicker, Cascader, Select } from "antd";
import type { Row } from "./types";

interface CollectionModalProps {
  open: boolean;
  collectionTarget: Row | null;
  batchCollectionTargets: Row[];
  collectionForm: any;
  collectionStorageOptions: any[];
  notaryOfficeOptions: { value: string }[];
  rows: Row[];
  collectionFiles: File[];
  onOk: () => void;
  onCancel: () => void;
  onFilesChange: (files: File[]) => void;
}

export default function CollectionModal({
  open,
  collectionTarget,
  batchCollectionTargets,
  collectionForm,
  collectionStorageOptions,
  notaryOfficeOptions,
  rows,
  collectionFiles,
  onOk,
  onCancel,
  onFilesChange,
}: CollectionModalProps) {
  const notaryInstitutionOptions = Array.from(
    new Set([
      ...notaryOfficeOptions.map((item) => item.value),
      ...rows
        .map((row) => String(row.data.notary_institution || "").trim())
        .filter(Boolean),
    ]),
  ).map((value) => ({ value }));

  return (
    <Modal
      open={open}
      title={
        batchCollectionTargets.length > 0
          ? `批量取证：已选 ${batchCollectionTargets.length} 条线索`
          : `单个取证：${collectionTarget?.serial_no || ""}`
      }
      okText="确认已取证"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={collectionForm} layout="vertical">
        <Form.Item
          label="取证机构"
          name="notary_institution"
          rules={[{ required: true, min: 2 }]}
        >
          <AutoComplete
            options={notaryInstitutionOptions}
            filterOption={(input, option) =>
              String(option?.value || "").includes(input)
            }
            placeholder="输入关键词选择或填写取证机构"
          />
        </Form.Item>
        <div className="form-grid">
          <Form.Item label="公证书号" name="notarization_no">
            <Input />
          </Form.Item>
          <Form.Item label="发票号码" name="invoice_no">
            <Input />
          </Form.Item>
        </div>
        <Form.Item
          label="取证日期"
          name="collected_at"
          rules={[{ required: true }]}
        >
          <DatePicker style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="warehouse_id" hidden>
          <Input />
        </Form.Item>
        <Form.Item name="storage_location_id" hidden>
          <Input />
        </Form.Item>
        <div className="form-grid">
          <Form.Item
            label="证物存放处"
            name="evidence_storage_path"
            rules={[{ required: true, message: "请选择证物存放处" }]}
          >
            <Cascader
              options={collectionStorageOptions}
              placeholder="请选择仓库及库位"
              showSearch
              onChange={(path) =>
                collectionForm.setFieldsValue({
                  warehouse_id: Number(path?.[0]) || undefined,
                  storage_location_id: Number(path?.[1]) || undefined,
                })
              }
            />
          </Form.Item>
          <Form.Item
            label="证物状态"
            name="evidence_status"
            initialValue="未入库"
          >
            <Select
              options={[
                "未入库",
                "已入库",
                "已出库",
                "已重新入库",
                "已销毁",
              ].map((value) => ({ value, label: value }))}
            />
          </Form.Item>
        </div>
        {batchCollectionTargets.length === 0 && (
          <Form.Item label="证据文件">
            <input
              type="file"
              multiple
              onChange={(event) =>
                onFilesChange(Array.from(event.target.files || []))
              }
            />
            {collectionFiles.length > 0 && (
              <div>已选择 {collectionFiles.length} 个文件</div>
            )}
          </Form.Item>
        )}
        <Form.Item label="取证说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
