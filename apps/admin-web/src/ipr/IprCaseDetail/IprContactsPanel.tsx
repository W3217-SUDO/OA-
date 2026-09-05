import { Card,Checkbox,Modal,Table } from "antd";
import type { CustomerContact,IprCaseContact,IprCaseCustomer,IprRecord } from "../types";

interface IprContactsPanelProps {
  detail: IprRecord;
  caseContacts: IprCaseContact[];
  contactOpen: boolean;
  contactCustomer: IprCaseCustomer | null;
  contactCandidates: CustomerContact[];
  documentContactIds: string[];
  technologyContactIds: string[];
  onCloseContactSelector: () => void;
  onSaveContacts: () => void;
  onDocumentContactChange: (ids: string[]) => void;
  onTechnologyContactChange: (ids: string[]) => void;
}

export function IprContactsPanel({
  detail,
  caseContacts,
  contactOpen,
  contactCustomer,
  contactCandidates,
  documentContactIds,
  technologyContactIds,
  onCloseContactSelector,
  onSaveContacts,
  onDocumentContactChange,
  onTechnologyContactChange,
}: IprContactsPanelProps) {
  return (
    <>
      <Card
        size="small"
        title="案件联系人"
        style={{ marginTop: 16 }}
      >
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: "尚未选择文书联系人或技术联系人" }}
          dataSource={caseContacts}
          columns={[
            { title: "客户", dataIndex: "customer_name", width: 150 },
            { title: "联系人", dataIndex: "name", width: 120 },
            {
              title: "角色",
              dataIndex: "contact_role",
              width: 100,
              render: (value) =>
                value === "document" ? "文书联系人" : "技术联系人",
            },
            {
              title: "电话",
              dataIndex: "phone",
              width: 140,
              render: (value) => value || "—",
            },
            {
              title: "邮箱",
              dataIndex: "email",
              ellipsis: true,
              render: (value) => value || "—",
            },
          ]}
        />
      </Card>

      <Modal
        open={contactOpen}
        title={
          contactCustomer
            ? `维护案件联系人：${contactCustomer.name}`
            : "维护案件联系人"
        }
        onCancel={onCloseContactSelector}
        onOk={onSaveContacts}
        okText="保存联系人"
        width={860}
      >
        <p style={{ color: "#666" }}>
          同一客户联系人可以同时承担文书联系人和技术联系人两种角色；已失效联系人不可再选择。
        </p>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={contactCandidates}
          columns={[
            { title: "姓名", dataIndex: "name", width: 130 },
            {
              title: "职务",
              dataIndex: "position",
              width: 140,
              render: (value) => value || "—",
            },
            {
              title: "电话",
              dataIndex: "phone",
              width: 160,
              render: (value) => value || "—",
            },
            {
              title: "邮箱",
              dataIndex: "email",
              ellipsis: true,
              render: (value) => value || "—",
            },
            {
              title: "文书联系人",
              width: 120,
              render: (_, row) => (
                <Checkbox
                  checked={documentContactIds.includes(row.id)}
                  onChange={(event) =>
                    onDocumentContactChange(
                      event.target.checked
                        ? [...new Set([...documentContactIds, row.id])]
                        : documentContactIds.filter((id) => id !== row.id)
                    )
                  }
                />
              ),
            },
            {
              title: "技术联系人",
              width: 120,
              render: (_, row) => (
                <Checkbox
                  checked={technologyContactIds.includes(row.id)}
                  onChange={(event) =>
                    onTechnologyContactChange(
                      event.target.checked
                        ? [...new Set([...technologyContactIds, row.id])]
                        : technologyContactIds.filter((id) => id !== row.id)
                    )
                  }
                />
              ),
            },
          ]}
        />
      </Modal>
    </>
  );
}
