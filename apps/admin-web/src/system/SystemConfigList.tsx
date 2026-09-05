import {
  Card,
  Empty,
  Table,
} from "antd";
import type { SystemConfig } from "./types";

interface SystemConfigListProps {
  configs: SystemConfig[];
}

export function SystemConfigList({ configs }: SystemConfigListProps) {
  const empty = (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
  );

  return (
    <>
      <Card className="panel system-focused" title="系统配置">
        <Table
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
              render: (value: Record<string, any>) => JSON.stringify(value),
            },
          ]}
          dataSource={configs}
          locale={{ emptyText: empty }}
          pagination={{
            defaultPageSize: 15,
            showSizeChanger: true,
            pageSizeOptions: ["10", "15", "20", "50", "100", "200"],
            showQuickJumper: true,
            showTotal: (total) => `共有${total}条`,
          }}
        />
      </Card>
    </>
  );
}
