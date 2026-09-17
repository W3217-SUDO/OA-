import { Descriptions } from "antd";
import type { CaseRow } from "../types";

// 主体的结构化字段与调查大厅编辑器一致，保留多主体而非只显示第一项。
function partyDetails(value: unknown) {
  const entries = Array.isArray(value) ? value : value ? [value] : [];
  if (!entries.length) return "—";
  return entries.map((entry, index) => {
    if (!entry || typeof entry !== "object") return <div key={index}>{String(entry || "—")}</div>;
    const item = entry as Record<string, unknown>;
    const fields: [string, unknown][] = [
      ["名称", item.name || item.producer || item.indictee], ["经营性质", item.nature],
      ["确认方式", item.confirmation_method], ["证件号码", item.identity_no],
      ["法定代表人", item.legal_representative], ["主体区域", item.region],
      ["工商地址", item.business_address || item.address],
    ];
    return <div key={index}>{fields.filter(([, value]) => value !== undefined && value !== null && String(value).trim()).map(([label, value]) => `${label}：${Array.isArray(value) ? value.join("/") : String(value)}`).join("；")}</div>;
  });
}

export function CaseClueDetails({ clue }: { clue: CaseRow }) {
  return (
        <Descriptions
          bordered
          size="small"
          column={2}
          items={[
            { key: "serial", label: "线索编号", children: clue.serial_no || "—" },
            { key: "method", label: "侵权方式", children: clue.data.infringement_method || clue.data.infringement_type || "—" },
            { key: "investigated", label: "调查时间", children: String(clue.data.investigated_at || clue.data.investigation_time || clue.data.investigation_date || "").replace("T", " ").slice(0, 19) || "—" },
            { key: "shop", label: "店铺名称", children: clue.data.shop_name || clue.data.store_name || clue.title || "—" },
            { key: "shop-id", label: "店铺Id", children: clue.data.shop_id || clue.data.store_id || "—" },
            { key: "shop-link", label: "店铺链接", children: clue.data.store_url || clue.data.shop_link || clue.data.store_link ? <a href={clue.data.store_url || clue.data.shop_link || clue.data.store_link} target="_blank" rel="noreferrer">{clue.data.store_url || clue.data.shop_link || clue.data.store_link}</a> : "—", span: 2 },
            { key: "region", label: "调查区域", children: clue.data.investigation_region || clue.data.region || "—" },
            { key: "address", label: "侵权地址", children: clue.data.infringement_address || clue.data.shop_address || clue.data.address || "—" },
            { key: "product", label: "产品名称", children: clue.data.product || "—", span: 2 },
            { key: "product-link", label: "产品链接", children: clue.data.product_url ? <a href={clue.data.product_url} target="_blank" rel="noreferrer">{clue.data.product_url}</a> : "—", span: 2 },
            { key: "scale", label: "规模", children: clue.data.sale_num || "—", span: 2 },
            { key: "producers", label: "生产商", children: partyDetails(clue.data.producers?.length ? clue.data.producers : clue.data.producer), span: 2 },
            { key: "subjects", label: "主体信息", children: partyDetails(clue.data.indictees?.length ? clue.data.indictees : clue.data.indictee || clue.data.subject), span: 2 },
            { key: "investigator", label: "调查员", children: clue.data.investigator_display_name || clue.owner_display_name || clue.owner || "—" },
            { key: "assistant", label: "调查辅助", children: clue.data.investigation_assistant_display_name || clue.data.investigation_assistant || "—" },
            { key: "remark", label: "调查员备注", children: clue.data.investigator_comment || clue.description || "—", span: 2 },
            { key: "status", label: "审批状态", children: clue.status || "—" },
            { key: "manager-comment", label: "管理人审核备注", children: clue.data.manager_review_comment || clue.data.review_comment || "—" },
            { key: "customer-comment", label: "客户审核备注", children: clue.data.customer_review_comment || "—", span: 2 },
          ]}
        />
  );
}
