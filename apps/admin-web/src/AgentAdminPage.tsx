import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Space, Tag, message } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { api } from "./api";
import Table from "./components/ResizableTable";

type Runtime = {
  ready: boolean;
  model: string;
  model_provider: string;
  model_configured: boolean;
  checkpoint_backend: string;
  max_concurrency: number;
  write_requires_approval: boolean;
  error?: string;
};
type SystemSkill = {
  id: string;
  name: string;
  category: string;
  description: string;
  source: string;
  available: boolean;
  unavailable_reason: string;
  quick_prompts: string[];
};
type UserLibrary = {
  username: string;
  display_name: string;
  skills: { id: string; name: string; category: string; enabled: boolean }[];
};
type Overview = { runtime: Runtime; system_skills: SystemSkill[]; user_libraries: UserLibrary[] };

const skillColumns = [
  { title: "名称", dataIndex: "name", width: 150 },
  { title: "分类", dataIndex: "category", width: 90 },
  { title: "说明", dataIndex: "description" },
  { title: "来源", dataIndex: "source", width: 260, ellipsis: true },
  {
    title: "状态",
    width: 200,
    render: (_: unknown, item: SystemSkill) => item.available
      ? <Tag color="success">可用</Tag>
      : <Tag color="warning">{item.unavailable_reason || "不可用"}</Tag>,
  },
];

const libraryColumns = [
  { title: "账号", dataIndex: "username", width: 160 },
  { title: "姓名", dataIndex: "display_name", width: 140 },
  { title: "技能数", width: 90, render: (_: unknown, item: UserLibrary) => item.skills.length },
  {
    title: "个人技能",
    render: (_: unknown, item: UserLibrary) => (
      <Space wrap size={[4, 4]}>
        {item.skills.map((skill) => <Tag key={skill.id} color={skill.enabled ? "blue" : undefined}>{skill.name}</Tag>)}
      </Space>
    ),
  },
];

// 管理员查看智能体运行状态、系统技能目录和各账号保存的个人技能。
export default function AgentAdminPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Overview>("/agent-admin/overview");
      setOverview(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "智能体中心加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const runtime = overview?.runtime;
  return (
    <Space orientation="vertical" size={12} style={{ width: "100%" }} data-testid="agent-admin-page">
      <Card
        title="运行状态"
        loading={loading && !overview}
        extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>刷新</Button>}
      >
        {runtime && (
          <>
            {runtime.error && <Alert type="error" showIcon title={runtime.error} style={{ marginBottom: 12 }} />}
            <Descriptions size="small" column={{ xs: 1, md: 3 }} bordered>
              <Descriptions.Item label="服务状态">
                <Tag color={runtime.ready ? "success" : "error"}>{runtime.ready ? "服务已连接" : "模型未就绪"}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模型服务商">{runtime.model_provider || "未配置"}</Descriptions.Item>
              <Descriptions.Item label="模型">{runtime.model || "未配置"}</Descriptions.Item>
              <Descriptions.Item label="检查点存储">{runtime.checkpoint_backend}</Descriptions.Item>
              <Descriptions.Item label="最大并发">{runtime.max_concurrency}</Descriptions.Item>
              <Descriptions.Item label="写入系统前确认">{runtime.write_requires_approval ? "需要用户确认" : "无需确认"}</Descriptions.Item>
            </Descriptions>
          </>
        )}
      </Card>
      <Card title="系统技能">
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          columns={skillColumns}
          dataSource={overview?.system_skills || []}
          pagination={false}
          scroll={{ x: 900 }}
        />
      </Card>
      <Card title="个人技能库（按账号）">
        <Table
          rowKey="username"
          size="small"
          loading={loading}
          columns={libraryColumns}
          dataSource={overview?.user_libraries || []}
          pagination={false}
          locale={{ emptyText: "还没有账号创建个人技能" }}
        />
      </Card>
    </Space>
  );
}
