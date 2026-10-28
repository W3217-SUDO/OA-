import { useEffect, useState } from "react";
import { Button, Form, Popconfirm, Tag, message } from "antd";
import { api } from "../api";

type DingTalkBinding = { user_id: string; name: string; primary: boolean };

/** 修改系统账号时列出该账号的全部钉钉绑定（主身份接收通知，其余只用于免登），可逐个解绑。 */
export function SystemUserDingTalkBindings({ userId, form }: { userId: number; form: ReturnType<typeof Form.useForm>[0] }) {
  const [items, setItems] = useState<DingTalkBinding[]>([]);
  const [loading, setLoading] = useState(false);
  const applyItems = (next: DingTalkBinding[]) => {
    setItems(next);
    // 表单里的“钉钉 UserId”跟着改成新的主身份，避免保存账号时把已解绑的写回去。
    form.setFieldValue(["profile", "dingtalk_user_id"], next.find((item) => item.primary)?.user_id || "");
  };
  useEffect(() => {
    let active = true;
    setLoading(true);
    api.get(`/system/users/${userId}/dingtalk-bindings`)
      .then(({ data }) => { if (active) setItems(data.items || []); })
      .catch(() => { if (active) message.error("钉钉绑定加载失败"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [userId]);
  const remove = async (item: DingTalkBinding) => {
    try {
      const { data } = await api.delete(`/system/users/${userId}/dingtalk-bindings/${encodeURIComponent(item.user_id)}`);
      applyItems(data.items || []);
      message.success("已解绑");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "解绑失败");
    }
  };
  return (
    <div className="system-user-dingtalk-bindings" style={{ gridColumn: "1 / -1", marginBottom: 16 }}>
      <div style={{ marginBottom: 6 }}>钉钉绑定{loading ? "（加载中…）" : `（${items.length} 个）`}</div>
      {items.map((item) => (
        <div key={item.user_id} style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 8, padding: "4px 0" }}>
          <span>{item.name || "未知姓名"}</span>
          <span style={{ color: "var(--oa-text-3, #8c8c8c)" }}>{item.user_id}</span>
          {item.primary && <Tag color="blue">主（接收通知）</Tag>}
          <Popconfirm title="解绑钉钉" description={`解绑 ${item.name || item.user_id}？解绑后该钉钉需重新输入账号密码绑定。`} okText="解绑" cancelText="取消" okButtonProps={{ danger: true }} onConfirm={() => remove(item)}>
            <Button size="small" danger>解绑</Button>
          </Popconfirm>
        </div>
      ))}
    </div>
  );
}
