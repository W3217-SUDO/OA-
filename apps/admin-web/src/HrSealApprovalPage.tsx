import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Form, message, Select, Space, Tag } from "antd";
import type { TableColumnsType } from "antd";
import Table from "./components/ResizableTable";
import { api } from "./api";

// 人事中心“用印审批设置”：所里审批人、行政用印人、各部门合同/用印审批路径（BUG20261031002 第④⑤步）。
type PeopleOption = { value: string; label: string; username: string; search_text?: string };
type DepartmentPath = {
  department_id: number;
  department: string;
  is_active: boolean;
  manager: string;
  first_override: string;
  second_override: string;
  first: string;
  second: string;
};
type SealApprovalSettings = {
  firm_approver: string;
  stamp_users: string[];
  department_paths: Record<string, string[]>;
  departments: DepartmentPath[];
  display_names: Record<string, string>;
};

export default function HrSealApprovalPage() {
  const [settings, setSettings] = useState<SealApprovalSettings | null>(null);
  const [people, setPeople] = useState<PeopleOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [firmApprover, setFirmApprover] = useState("");
  const [stampUsers, setStampUsers] = useState<string[]>([]);
  const [paths, setPaths] = useState<Record<string, string[]>>({});

  const apply = (data: SealApprovalSettings) => {
    setSettings(data);
    setFirmApprover(data.firm_approver || "");
    setStampUsers(data.stamp_users || []);
    setPaths(data.department_paths || {});
  };
  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<SealApprovalSettings>("/hr/seal-approval-settings");
      apply(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "用印审批设置加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
    void api.get<{ items?: PeopleOption[] }>("/people/options")
      .then(({ data }) => setPeople(data.items || []))
      .catch(() => setPeople([]));
  }, []);

  const personOptions = useMemo(
    () => people.map((person) => ({ value: person.username, label: person.label, search: person.search_text || person.label })),
    [people],
  );
  const nameOf = (username: string) => {
    if (!username) return "";
    return people.find((person) => person.username === username)?.label || settings?.display_names?.[username] || username;
  };
  const setStep = (departmentId: number, index: 0 | 1, value: string) => {
    setPaths((current) => {
      const steps = [...(current[String(departmentId)] || ["", ""])];
      steps[index] = value || "";
      return { ...current, [String(departmentId)]: steps };
    });
  };
  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put<SealApprovalSettings>("/hr/seal-approval-settings", {
        firm_approver: firmApprover || "",
        stamp_users: stampUsers,
        department_paths: paths,
      });
      apply(data);
      message.success("用印审批设置已保存.");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败.");
    } finally {
      setSaving(false);
    }
  };

  const columns: TableColumnsType<DepartmentPath> = [
    { title: "部门", dataIndex: "department", width: 160, render: (value, row) => <Space>{value}{row.is_active ? null : <Tag>停用</Tag>}</Space> },
    {
      title: "第一步（默认本部门负责人）",
      key: "first",
      width: 280,
      render: (_value, row) => (
        <Select
          allowClear
          showSearch
          style={{ width: "100%" }}
          optionFilterProp="search"
          value={(paths[String(row.department_id)] || [])[0] || undefined}
          placeholder={row.manager ? `部门负责人：${nameOf(row.manager)}` : "未设负责人，这一步跳过"}
          options={personOptions}
          onChange={(value) => setStep(row.department_id, 0, value || "")}
        />
      ),
    },
    {
      title: "第二步（默认所里审批人）",
      key: "second",
      width: 280,
      render: (_value, row) => (
        <Select
          allowClear
          showSearch
          style={{ width: "100%" }}
          optionFilterProp="search"
          value={(paths[String(row.department_id)] || [])[1] || undefined}
          placeholder={firmApprover ? `所里审批人：${nameOf(firmApprover)}` : "所里审批人未设置"}
          options={personOptions}
          onChange={(value) => setStep(row.department_id, 1, value || "")}
        />
      ),
    },
    {
      title: "审批路径",
      key: "path",
      render: (_value, row) => {
        const steps = paths[String(row.department_id)] || ["", ""];
        const first = steps[0] || row.manager;
        const second = steps[1] || firmApprover;
        return [first ? nameOf(first) : "（跳过）", second ? nameOf(second) : "（所里审批人未设置）", "行政用印"].join(" → ");
      },
    },
  ];

  return (
    <Card className="panel" title="用印审批设置" loading={loading && !settings}>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        title="合同审批与用印是同一个流程：本部门负责人 → 所里审批人；勾选“同步用印”或单独申请用印的，审批通过后转行政用印。"
        description="每个部门默认按上面的顺序走，可在下表把某一步换成别的人；留空就按默认。提交人自己就是第一步审批人的，第一步跳过；部门没设负责人的，第一步也跳过。"
      />
      <Form layout="vertical">
        <Space wrap align="start" size={24}>
          <Form.Item label="所里审批人" extra="全所一人；没设置时不能提交合同审批和用印申请" style={{ minWidth: 280 }}>
            <Select allowClear showSearch optionFilterProp="search" value={firmApprover || undefined} placeholder="请选择" options={personOptions} onChange={(value) => setFirmApprover(value || "")} />
          </Form.Item>
          <Form.Item label="行政用印人" extra="设了以后只有他们能盖章；没设时仍由有用印权限的人处理" style={{ minWidth: 360 }}>
            <Select mode="multiple" allowClear showSearch optionFilterProp="search" value={stampUsers} placeholder="请选择" options={personOptions} onChange={(value) => setStampUsers(value)} />
          </Form.Item>
        </Space>
      </Form>
      <Table
        rowKey="department_id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={settings?.departments || []}
        scroll={{ x: 960 }}
        pagination={false}
      />
      <div style={{ marginTop: 16 }}>
        <Button type="primary" loading={saving} onClick={() => void save()}>保存</Button>
      </div>
    </Card>
  );
}
