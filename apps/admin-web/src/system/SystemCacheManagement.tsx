import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  Popconfirm,
  Space,
  Table,
} from "antd";
import { ReloadOutlined, ClearOutlined } from "@ant-design/icons";
import type { CacheRow, CacheSummary } from "./types";
import { formatTime } from "./constants";

interface SystemCacheManagementProps {
  caches: CacheRow[];
  cacheSummary: CacheSummary | null;
  cacheActionPending: boolean;
  cacheTotal: number;
  cachePage: number;
  cachePageSize: number;
  cacheJumpPage: string;
  selectedCacheKeys: string[];
  onSelectedCacheKeysChange: (keys: string[]) => void;
  onCacheJumpPageChange: (value: string) => void;
  onLoadCaches: (page: number, pageSize: number) => void;
  onClearCache: (row: CacheRow) => void;
  onClearSelectedCaches: () => void;
  onClearAllCaches: () => void;
  onJumpToCachePage: () => void;
}

export function SystemCacheManagement({
  caches,
  cacheSummary,
  cacheActionPending,
  cacheTotal,
  cachePage,
  cachePageSize,
  cacheJumpPage,
  selectedCacheKeys,
  onSelectedCacheKeysChange,
  onCacheJumpPageChange,
  onLoadCaches,
  onClearCache,
  onClearSelectedCaches,
  onClearAllCaches,
  onJumpToCachePage,
}: SystemCacheManagementProps) {
  const empty = (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
  );

  return (
    <Card className="panel system-focused" title="缓存管理">
      <Alert
        type="info"
        showIcon
        message={cacheSummary
          ? `当前缓存 ${cacheSummary.cache_buckets} 个桶、${cacheSummary.cache_entries} 条条目；可清理 ${cacheSummary.clearable_caches} 项。`
          : "正在读取缓存统计信息。"}
        description={cacheSummary?.scope || "缓存统计仅包含本服务可管理的进程内存缓存。"}
        style={{ marginBottom: 12 }}
      />
      <Table
        rowKey="key"
        size="small"
        rowSelection={{
          selectedRowKeys: selectedCacheKeys,
          onChange: (keys) => onSelectedCacheKeysChange(keys.map(String)),
          getCheckboxProps: (row: CacheRow) => ({ disabled: !row.clearable }),
        }}
        title={() => (
          <Space>
            <Button disabled={cacheActionPending} onClick={() => onLoadCaches(cachePage, cachePageSize)} icon={<ReloadOutlined />}>刷新列表</Button>
            <Popconfirm title="确认清除选中的缓存？" onConfirm={onClearSelectedCaches}>
              <Button loading={cacheActionPending} disabled={!selectedCacheKeys.length} danger>清除选中缓存</Button>
            </Popconfirm>
            <Popconfirm
              title="确认清除全部缓存？"
              description="此操作会清除当前 API 进程的所有内存缓存，之后请求会重新加载数据。"
              okText="确认清除"
              cancelText="取消"
              onConfirm={onClearAllCaches}
            >
              <Button type="primary" loading={cacheActionPending} danger>清除全部缓存</Button>
            </Popconfirm>
          </Space>
        )}
        columns={[
          {
            title: "序号",
            key: "no",
            width: 70,
            render: (_v: unknown, _r: unknown, i: number) => i + 1,
          },
          { title: "缓存名称", dataIndex: "name" },
          { title: "缓存键值", dataIndex: "key" },
          { title: "存储方式", dataIndex: "storage", width: 130 },
          { title: "缓存桶", dataIndex: "bucket_count", width: 90 },
          { title: "缓存条目", dataIndex: "entry_count", width: 100 },
          { title: "说明", dataIndex: "description", ellipsis: true },
          { title: "上次清理", dataIndex: "last_cleared_at", width: 175, render: (value: string) => formatTime(value) },
          {
            title: "操作",
            key: "action",
            width: 110,
            render: (_v: unknown, row: CacheRow) => (
              row.clearable ? (
                <Popconfirm title="确认清空此缓存？" onConfirm={() => onClearCache(row)}>
                  <Button type="link" disabled={cacheActionPending} danger icon={<ClearOutlined />}>清空</Button>
                </Popconfirm>
              ) : <span style={{ color: "#8c8c8c" }}>未启用缓存</span>
            ),
          },
        ]}
        dataSource={caches}
        scroll={{ x: 1250 }}
        locale={{ emptyText: empty }}
        pagination={{ current: cachePage, pageSize: cachePageSize, total: cacheTotal, showTotal: (total) => `共有${total}条`, showSizeChanger: true, pageSizeOptions: ["10", "15", "20", "50", "100", "200"], showQuickJumper: { goButton: "GO" }, onChange: (page, pageSize) => { onLoadCaches(page, pageSize); } }}
      />
      <Space size="small" style={{ float: "right", marginTop: -40, marginRight: 8 }}>
        <Input
          aria-label="缓存页码"
          value={cacheJumpPage}
          onChange={(event) => onCacheJumpPageChange(event.target.value.replace(/\D/g, ""))}
          onPressEnter={onJumpToCachePage}
          placeholder="页码"
          size="small"
          style={{ width: 64 }}
        />
        <Button size="small" onClick={onJumpToCachePage}>GO</Button>
      </Space>
    </Card>
  );
}
