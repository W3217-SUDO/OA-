import { Button, DatePicker, Descriptions, Input, Modal, Space, Table, Tag } from "antd";
import dayjs from "dayjs";
import type { SealAsset, AssetAuditFilters } from "./types";
import type { SealAssetAuditRow } from "../sealWorkflowPolicy";
import { assetColors, personDisplayName } from "./constants";
import { sealAssetAuditPagination } from "../sealWorkflowPolicy";

interface SealAssetAuditModalProps {
  open: boolean;
  asset: SealAsset | null;
  rows: SealAssetAuditRow[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  filters: AssetAuditFilters;
  onClose: () => void;
  onFiltersChange: (filters: AssetAuditFilters) => void;
  onPageChange: (page: number, pageSize: number) => void;
  onQuery: () => void;
  onReset: () => void;
}

export function SealAssetAuditModal({
  open,
  asset,
  rows,
  total,
  page,
  pageSize,
  loading,
  filters,
  onClose,
  onFiltersChange,
  onPageChange,
  onQuery,
  onReset,
}: SealAssetAuditModalProps) {
  return (
    <Modal
      open={open}
      width={920}
      title={asset ? `印章详情与审计：${asset.name}（${asset.code}）` : "印章详情与审计"}
      footer={<Button onClick={onClose}>关闭</Button>}
      onCancel={onClose}
    >
      {asset && (
        <>
          <Descriptions
            bordered
            size="small"
            column={3}
            items={[
              { key: "code", label: "印章编号", children: asset.code },
              { key: "name", label: "印章名称", children: asset.name },
              { key: "type", label: "印章类别", children: asset.seal_type },
              { key: "custodian", label: "保管人", children: asset.custodian },
              { key: "location", label: "存放位置", children: asset.location || "—" },
              { key: "status", label: "状态", children: <Tag color={assetColors[asset.status] || "blue"}>{asset.status}</Tag> },
              { key: "usage", label: "累计用印", children: `${asset.usage_count} 份` },
              { key: "last_used", label: "最近使用", children: asset.last_used_at ? dayjs(asset.last_used_at).format("YYYY-MM-DD HH:mm") : "—" },
              { key: "remark", label: "备注", children: asset.remark || "—", span: 3 },
            ]}
          />
          <Space wrap style={{ margin: "12px 0" }}>
            <Input
              placeholder="动作"
              value={filters.action}
              onChange={(event) => onFiltersChange({ ...filters, action: event.target.value })}
              style={{ width: 150 }}
            />
            <Input
              placeholder="操作人"
              value={filters.operator}
              onChange={(event) => onFiltersChange({ ...filters, operator: event.target.value })}
              style={{ width: 130 }}
            />
            <Input
              placeholder="关键词（动作/操作人/备注）"
              value={filters.keyword}
              onChange={(event) => onFiltersChange({ ...filters, keyword: event.target.value })}
              style={{ width: 220 }}
            />
            <DatePicker.RangePicker
              value={filters.date_from && filters.date_to ? [dayjs(filters.date_from), dayjs(filters.date_to)] : null}
              onChange={(values) => onFiltersChange({ ...filters, date_from: values?.[0]?.format("YYYY-MM-DD") || "", date_to: values?.[1]?.format("YYYY-MM-DD") || "" })}
            />
            <Button type="primary" onClick={onQuery}>查询</Button>
            <Button onClick={onReset}>清空</Button>
          </Space>
          <Table
            rowKey="id"
            size="small"
            loading={loading}
            dataSource={rows}
            locale={{ emptyText: "暂无审计记录" }}
            columns={[
              { title: "动作", dataIndex: "action", width: 150 },
              { title: "操作人", dataIndex: "operator_display_name", width: 110, render: personDisplayName },
              { title: "备注", dataIndex: "comment", ellipsis: true },
              { title: "时间", dataIndex: "created_at", width: 170, render: (value: string) => dayjs(value).format("YYYY-MM-DD HH:mm:ss") },
            ]}
            pagination={{
              current: page,
              pageSize: pageSize,
              total: total,
              showSizeChanger: sealAssetAuditPagination.showSizeChanger,
              pageSizeOptions: sealAssetAuditPagination.pageSizeOptions.map(String),
              showQuickJumper: sealAssetAuditPagination.showQuickJumper,
              showTotal: sealAssetAuditPagination.showTotal,
              onChange: onPageChange,
            }}
          />
        </>
      )}
    </Modal>
  );
}
