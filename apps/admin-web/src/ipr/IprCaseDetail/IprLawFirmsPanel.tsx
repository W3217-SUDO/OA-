import { Button,Card,Modal,Table } from "antd";
import type { IprLawFirm,IprLawFirmCandidate,IprRecord } from "../types";

interface IprLawFirmsPanelProps {
  detail: IprRecord;
  caseLawFirms: IprLawFirm[];
  lawFirmOpen: boolean;
  lawFirmCandidates: IprLawFirmCandidate[];
  lawFirmSelection: number[];
  onOpenLawFirmSelector: () => void;
  onCloseLawFirmSelector: () => void;
  onSaveLawFirms: () => void;
  onLawFirmSelectionChange: (keys: number[]) => void;
}

export function IprLawFirmsPanel({
  detail,
  caseLawFirms,
  lawFirmOpen,
  lawFirmCandidates,
  lawFirmSelection,
  onOpenLawFirmSelector,
  onCloseLawFirmSelector,
  onSaveLawFirms,
  onLawFirmSelectionChange,
}: IprLawFirmsPanelProps) {
  return (
    <>
      <Card
        size="small"
        title="协作律所"
        style={{ marginTop: 16 }}
        extra={
          detail.status === "草稿" ||
          detail.status === "已驳回" ||
          detail.status === "在办" ? (
            <Button size="small" onClick={onOpenLawFirmSelector}>
              维护协作律所
            </Button>
          ) : null
        }
      >
        {caseLawFirms.length ? (
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={caseLawFirms}
            columns={[
              { title: "律所编号", dataIndex: "code", width: 140 },
              { title: "律所名称", dataIndex: "name", width: 220 },
              {
                title: "电话",
                dataIndex: "phone",
                width: 150,
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
        ) : (
          "暂未选择协作律所"
        )}
      </Card>

      <Modal
        open={lawFirmOpen}
        title="选择协作律所"
        onCancel={onCloseLawFirmSelector}
        onOk={onSaveLawFirms}
        okText="保存关联"
        width={760}
      >
        <p style={{ color: "#666" }}>
          仅显示启用的律所；保存时会以当前勾选结果替换本案件的协作律所。
        </p>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={lawFirmCandidates}
          rowSelection={{
            selectedRowKeys: lawFirmSelection,
            onChange: (keys) => onLawFirmSelectionChange(keys.map(Number)),
          }}
          columns={[
            { title: "编号", dataIndex: "code", width: 130 },
            { title: "律所名称", dataIndex: "name", width: 230 },
            {
              title: "电话",
              dataIndex: "phone",
              width: 150,
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
      </Modal>
    </>
  );
}
