import { useEffect, useRef, useState } from "react";
import { AutoComplete, DatePicker, Form, Input, Select } from "antd";
import type { FormInstance } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import { fillNotaryNumber, hasNotaryPlaceholder } from "./notaryNumber";
import type { WarehouseCatalogItem } from "./types";

type NotaryOption = { value: string; template?: string };

// 501336（fwl 11-04）：案件和调查大厅里“修改取证信息”共用：取证机构可选公证处并按模板填公证书号（同 501325），
// 证物存放处列出启用的仓库库位可直接选，也可手填。
export function EvidenceInfoFields({ form, open }: { form: FormInstance; open: boolean }) {
  const [notaryOffices, setNotaryOffices] = useState<NotaryOption[]>([]);
  const [storageOptions, setStorageOptions] = useState<{ value: string }[]>([]);
  useEffect(() => {
    if (!open) return;
    api.get("/system/parameters/options", { params: { category: "notary_office" } })
      .then(({ data }) => setNotaryOffices((data.items || [])
        .map((item: { name?: string; number_template?: string }) => ({ value: String(item.name || "").trim(), template: String(item.number_template || "").trim() }))
        .filter((item: NotaryOption, index: number, all: NotaryOption[]) => item.value && all.findIndex((other) => other.value === item.value) === index)))
      .catch(() => setNotaryOffices([]));
    api.get("/investigations/evidence-storage-options")
      .then(({ data }) => setStorageOptions((data.items as WarehouseCatalogItem[] || []).filter((warehouse) => warehouse.is_active)
        .flatMap((warehouse) => {
          const locations = (warehouse.locations || []).filter((location) => location.is_active);
          return locations.length ? locations.map((location) => ({ value: `${warehouse.name} / ${location.name}` })) : [{ value: warehouse.name }];
        })))
      .catch(() => setStorageOptions([]));
  }, [open]);

  const institution = Form.useWatch("notary_institution", form);
  const collectedAt = Form.useWatch("collected_at", form);
  const autoFilled = useRef("");
  useEffect(() => { if (open) autoFilled.current = ""; }, [open]);
  useEffect(() => {
    const office = notaryOffices.find((item) => item.value === String(institution || "").trim());
    if (!office?.template) return;
    const year = collectedAt && dayjs.isDayjs(collectedAt) ? collectedAt.year() : dayjs().year();
    const filled = fillNotaryNumber(office.template, year);
    const current = String(form.getFieldValue("certificate_no") || "");
    if (!current || current === autoFilled.current) {
      form.setFieldsValue({ certificate_no: filled });
      autoFilled.current = filled;
    }
  }, [institution, collectedAt, notaryOffices, form]);

  const contains = (input: string, option?: { value?: string }) => String(option?.value || "").includes(input);
  return <>
    <Form.Item label="取证机构" name="notary_institution" rules={[{ required: true, message: "请输入取证机构" }]}>
      <AutoComplete options={notaryOffices.map(({ value }) => ({ value }))} filterOption={contains} placeholder="选择或填写取证机构" />
    </Form.Item>
    <div className="form-grid">
      <Form.Item label="公证书号" name="certificate_no" rules={[{ validator: (_, value) => hasNotaryPlaceholder(value)
        ? Promise.reject(new Error("请把公证书号里的 xxxxx 换成实际编号")) : Promise.resolve() }]}><Input /></Form.Item>
      <Form.Item label="取证时间" name="collected_at" rules={[{ required: true, message: "请选择取证时间" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
      <Form.Item label="发票号码" name="invoice_no"><Input /></Form.Item>
      <Form.Item label="证物状态" name="evidence_status"><Select options={["未入库", "已入库", "已出库", "已重新入库", "已销毁"].map((value) => ({ value, label: value }))} /></Form.Item>
    </div>
    <Form.Item label="证物存放处" name="storage_location">
      <AutoComplete options={storageOptions} filterOption={contains} placeholder="选择仓库库位，或直接填写" />
    </Form.Item>
  </>;
}
