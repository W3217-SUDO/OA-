import { useEffect, useState } from "react";
import {
  Card,
  Empty,
  message,
  Switch,
  Table,
  Tag,
} from "antd";
import { api } from "../api";
import type { SystemConfig } from "./types";

interface SystemConfigListProps {
  configs: SystemConfig[];
}

export function SystemConfigList({ configs }: SystemConfigListProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [autoReviewSaving, setAutoReviewSaving] = useState(false);
  const [autoReviewOverride, setAutoReviewOverride] = useState<SystemConfig | null>(null);
  const empty = (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
  );

  useEffect(() => {
    setAutoReviewOverride(null);
  }, [configs]);

  const saveAutoReview = async (enabled: boolean) => {
    setAutoReviewSaving(true);
    try {
      const { data } = await api.patch<SystemConfig>("/system/configs/conflict_auto_review", { value: { enabled } });
      if (data.value?.enabled !== enabled) throw new Error("服务器返回的自动利冲审查配置不一致");
      setAutoReviewOverride(data);
      message.success("配置已保存");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.message || "自动利冲审查配置保存失败");
    } finally {
      setAutoReviewSaving(false);
    }
  };

  return (
    <>
      <Card className="panel system-focused" title="系统配置">
        <Table<SystemConfig>
          rowKey="key"
          size="small"
          columns={[
            {
              title: "序号",
              key: "no",
              width: 70,
              render: (_v: unknown, _r: unknown, i: number) => i + 1,
            },
            { title: "配置项组", dataIndex: "group", width: 150 },
            { title: "配置项名称", dataIndex: "label", width: 180 },
            { title: "配置项主键", dataIndex: "key", width: 190 },
            {
              title: "键值",
              dataIndex: "value",
              render: (value: Record<string, any>, row: SystemConfig) => {
                if (row.key !== "conflict_auto_review") return JSON.stringify(value);
                const current = autoReviewOverride || row;
                const enabled = current.value?.enabled === true;
                const statusAvailable = typeof current.ready === "boolean" && typeof current.effective === "boolean";
                return (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <Switch
                      aria-label="自动利冲审查总开关"
                      checked={enabled}
                      loading={autoReviewSaving}
                      disabled={autoReviewSaving || (!enabled && current.ready !== true)}
                      onChange={(checked) => void saveAutoReview(checked)}
                    />
                    <Tag color={current.effective ? "green" : "default"}>
                      {current.effective ? "自动审查运行中" : "自动审查未运行"}
                    </Tag>
                    <span style={{ color: statusAvailable ? "#666" : "#cf1322" }}>
                      {statusAvailable ? current.reason || (enabled ? "已开启" : "已关闭") : "自动利冲审查状态不可用"}
                    </span>
                  </div>
                );
              },
            },
          ]}
          dataSource={configs}
          locale={{ emptyText: empty }}
          pagination={{
            current: page,
            pageSize,
            showSizeChanger: true,
            pageSizeOptions: ["10", "15", "20", "50", "100", "200"],
            showQuickJumper: true,
            showTotal: (total) => `共有${total}条`,
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPage);
              setPageSize(nextPageSize);
            },
          }}
        />
      </Card>
    </>
  );
}
