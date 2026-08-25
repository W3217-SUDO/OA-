import { useEffect, useState } from "react";
import { Alert, Card, Descriptions, Spin, Table, Tag, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { api } from "./api";

type LegacyCustomer = {
  legacy_customer_id: number;
  legacy_customer_no: string;
  legacy_customer_name: string;
  relationship_state: string;
  identity_state: string;
  is_primary: boolean;
  current_customer_record_id: number | null;
};

type LegacyContact = {
  legacy_contact_id: number;
  legacy_customer_id: number;
  legacy_contact_name: string;
  email: string;
  mobilephone: string;
  contact_role: string | null;
  relationship_state: string;
  identity_state: string;
  current_customer_record_id: number | null;
};

type LegacyHistory = {
  case: { case_no: string; title: string; contract_no: string; relationship_state: string };
  historical_customers: LegacyCustomer[];
  historical_contacts: LegacyContact[];
};

export function IprLegacyHistoryRelations({ legacyCaseId, onOpenCurrentCustomer }: {
  legacyCaseId: number;
  onOpenCurrentCustomer: (customerRecordId: number) => void;
}) {
  const [data, setData] = useState<LegacyHistory | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setData(null); setError("");
    api.get<LegacyHistory>(`/legacy-ipr-history/cases/${legacyCaseId}`)
      .then(response => { if (active) setData(response.data); })
      .catch(() => { if (active) setError("历史知识产权关系暂不可用"); });
    return () => { active = false; };
  }, [legacyCaseId]);

  const customerColumns: TableColumnsType<LegacyCustomer> = [
    { title: "历史客户", render: (_, row) => `${row.legacy_customer_no || "-"} ${row.legacy_customer_name || "-"}` },
    { title: "关系状态", dataIndex: "relationship_state", width: 180 },
    { title: "主客户", width: 90, render: (_, row) => row.is_primary ? <Tag color="green">是</Tag> : <Tag>否</Tag> },
    { title: "当前客户", width: 220, render: (_, row) => row.current_customer_record_id == null
      ? <Tag>仅旧系统身份，未映射当前客户</Tag>
      : <Typography.Link onClick={() => onOpenCurrentCustomer(row.current_customer_record_id!)}>打开当前客户 #{row.current_customer_record_id}</Typography.Link> },
  ];
  const contactColumns: TableColumnsType<LegacyContact> = [
    { title: "历史联系人", dataIndex: "legacy_contact_name" },
    { title: "联系方式", render: (_, row) => [row.email, row.mobilephone].filter(Boolean).join(" / ") || "-" },
    { title: "角色", dataIndex: "contact_role", width: 120 },
    { title: "关系状态", dataIndex: "relationship_state", width: 180 },
    { title: "当前客户", width: 220, render: (_, row) => row.current_customer_record_id == null
      ? <Tag>仅旧系统身份，未映射当前客户</Tag>
      : <Typography.Link onClick={() => onOpenCurrentCustomer(row.current_customer_record_id!)}>打开当前客户 #{row.current_customer_record_id}</Typography.Link> },
  ];

  if (error) return <Alert type="warning" showIcon message={error} />;
  if (!data) return <Spin size="small" />;
  return <Card size="small" title="历史关系">
    <Descriptions size="small" column={3} items={[
      { key: "case", label: "历史案号", children: data.case.case_no || "-" },
      { key: "contract", label: "合同号", children: data.case.contract_no || "-" },
      { key: "state", label: "迁移状态", children: data.case.relationship_state },
    ]} />
    <Table rowKey="legacy_customer_id" size="small" columns={customerColumns} dataSource={data.historical_customers} pagination={false} />
    <Table rowKey="legacy_contact_id" size="small" columns={contactColumns} dataSource={data.historical_contacts} pagination={false} />
  </Card>;
}
