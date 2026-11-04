import { useEffect, useRef } from "react";
import dayjs from "dayjs";
import { fillNotaryNumber, hasNotaryPlaceholder } from "./notaryNumber";
import { Modal, Form, AutoComplete, Input, DatePicker, Cascader, Select, Alert, Spin } from "antd";
import type { Row } from "./types";

interface CollectionModalProps {
  open: boolean;
  collectionTarget: Row | null;
  batchCollectionTargets: Row[];
  collectionForm: any;
  collectionStorageOptions: any[];
  collectionStorageLoading: boolean;
  collectionStorageError: string;
  notaryOfficeOptions: { value: string; template?: string }[];
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
  collectionStorageLoading,
  collectionStorageError,
  notaryOfficeOptions,
  rows,
  collectionFiles,
  onOk,
  onCancel,
  onFilesChange,
}: CollectionModalProps) {
  // 501325：选取证机构或改取证日期时，公证书号还空着或还是上次自动填的，就按模板重新填。
  const autoFilled = useRef("");
  useEffect(() => { if (open) autoFilled.current = ""; }, [open, collectionTarget?.id]);
  const fillNotaryFromTemplate = (values: { notary_institution?: string; collected_at?: dayjs.Dayjs; notarization_no?: string }) => {
    const office = notaryOfficeOptions.find((item) => item.value === String(values.notary_institution || "").trim());
    const year = values.collected_at && dayjs.isDayjs(values.collected_at) ? values.collected_at.year() : dayjs().year();
    const filled = fillNotaryNumber(office?.template, year);
    const current = String(values.notarization_no || "");
    if (!current || current === autoFilled.current) {
      collectionForm.setFieldsValue({ notarization_no: filled || (current === autoFilled.current ? "" : current) });
      autoFilled.current = filled;
    }
  };
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
      <Form form={collectionForm} layout="vertical" onValuesChange={(changed, all) => {
        if ("notary_institution" in changed || "collected_at" in changed) fillNotaryFromTemplate(all);
      }}>
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
          <Form.Item label="公证书号" name="notarization_no" rules={[{ validator: (_, value) => hasNotaryPlaceholder(value)
            ? Promise.reject(new Error("请把公证书号里的 xxxxx 换成实际编号")) : Promise.resolve() }]}>
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
            validateStatus={collectionStorageError ? "error" : undefined}
            help={collectionStorageError || undefined}
            name="evidence_storage_path"
          >
            <Cascader
              options={collectionStorageOptions}
              disabled={collectionStorageLoading || !!collectionStorageError}
              notFoundContent={collectionStorageLoading ? <Spin size="small" /> : "暂无可用库位"}
              // BUG20261029003：取证时证物存放处选填，入库时再选也可以。
              placeholder="选填，可在证物入库时再选"
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
        {!collectionStorageLoading && !collectionStorageError && !collectionStorageOptions.length && (
          <Alert type="info" showIcon message="暂无可用库位，可先不填，证物入库时再选" />
        )}
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
