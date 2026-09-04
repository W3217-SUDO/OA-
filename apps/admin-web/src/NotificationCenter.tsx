import { useEffect, useState } from "react";
import { Badge, Button, Drawer, Empty, List, Modal, Space, Tag, Tooltip } from "antd";
import { BellOutlined, CheckOutlined } from "@ant-design/icons";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberTaskDetailTarget } from "./taskDetailNavigation";
import { rememberInvestigationDetailTarget } from "./investigationDetailNavigation";
import { rememberBusinessRecordDetailTarget } from "./businessRecordDetailNavigation";

type Notice = {
  id: number;
  source_type: string;
  source_id: number | null;
  title: string;
  content: string;
  level: string;
  is_read: boolean;
  created_at: string;
};

const colors: Record<string, string> = { error: "red", warning: "orange", info: "blue" };
const routes: Record<string, string> = {task:'task-reminders',finance:'finance-audit',finance_package:'finance-fee-query',finance_settlement:'finance-fee-query',finance_archive_settlement:'finance-fee-query',contract:'contract-audit',case:'case-schedule'};

export default function NotificationCenter({ onNavigate }: { onNavigate: (key: string) => void }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notice[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedNotice, setSelectedNotice] = useState<Notice | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/notifications");
      setItems(data.items);
      setUnread(data.unread);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const notificationsUpdated = () => { void load(); };
    void load();
    const timer = window.setInterval(load, 30000);
    window.addEventListener('sunhold:notifications-updated',notificationsUpdated);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('sunhold:notifications-updated',notificationsUpdated);
    };
  }, []);

  const read = async (item: Notice) => {
    if (!item.is_read) await api.post(`/notifications/${item.id}/read`);
    const nextNotice = { ...item, is_read: true };
    setItems((rows) => rows.map((row) => row.id === item.id ? { ...row, is_read: true } : row));
    setUnread((value) => Math.max(0, value - (item.is_read ? 0 : 1)));
    if (item.source_type === "contract" && item.source_id) rememberContractDetailTarget({ id: item.source_id });
    if (item.source_type === "case" && item.source_id) rememberCaseDetailTarget({ id: item.source_id });
    if (item.source_type === "task" && item.source_id) rememberTaskDetailTarget({ id: item.source_id });
    let iprWarningRoute = "";
    if (item.source_type === "ipr_warning" && item.source_id) {
      try {
        const { data } = await api.get<{ data?: { case_kind?: string } }>(`/ipr/cases/${item.source_id}`);
        window.sessionStorage.setItem("sunhold:ipr-warning-target", String(item.source_id));
        window.dispatchEvent(new Event("sunhold:ipr-warning-target"));
        iprWarningRoute = data.data?.case_kind === "商标" ? "ipr-trademark" : "ipr-patent";
      } catch (error: any) {
        setSelectedNotice(nextNotice);
        return;
      }
    }
    if (["clue", "notary", "evidence"].includes(item.source_type) && item.source_id) rememberInvestigationDetailTarget({ id: item.source_id, module: item.source_type });
    if (["finance", "finance_package", "finance_settlement", "finance_archive_settlement"].includes(item.source_type) && item.source_id) rememberBusinessRecordDetailTarget({ id: item.source_id, module: item.source_type as "finance" | "finance_package" | "finance_settlement" | "finance_archive_settlement" });
    const route = iprWarningRoute || routes[item.source_type] || (["clue", "notary", "evidence"].includes(item.source_type) ? item.source_type : "");
    if (route) {
      onNavigate(route);
      setOpen(false);
      return;
    }
    setSelectedNotice(nextNotice);
  };

  const readAll = async () => {
    await api.post("/notifications/read-all");
    setItems((rows) => rows.map((item) => ({ ...item, is_read: true })));
    setUnread(0);
  };

  return (
    <>
      <Tooltip title="消息通知">
        <Badge count={unread} size="small" overflowCount={99}>
          <Button type="text" icon={<BellOutlined />} onClick={() => { setOpen(true); void load(); }} />
        </Badge>
      </Tooltip>
      <Drawer
        size={440}
        open={open}
        title={<Space>消息通知{unread > 0 && <Tag color="red">{unread} 条未读</Tag>}</Space>}
        onClose={() => setOpen(false)}
        footer={(
          <Space style={{ width: "100%", justifyContent: "space-between" }}>
            <Button
              type="link"
              onClick={() => {
                onNavigate("user-messages");
                setOpen(false);
              }}
            >
              更多内部消息
            </Button>
            <Button size="small" icon={<CheckOutlined />} disabled={!unread} onClick={readAll}>全部已读</Button>
          </Space>
        )}
      >
        <List
          loading={loading}
          dataSource={items}
          locale={{ emptyText: <Empty description="暂无消息" /> }}
          renderItem={(item) => (
            <List.Item
              className={item.is_read ? "notice-read" : "notice-unread"}
              onClick={() => void read(item)}
              style={{ cursor: "pointer", padding: "14px 10px", background: item.is_read ? "transparent" : "#f0fff7" }}
            >
              <List.Item.Meta
                title={<Space><Tag color={colors[item.level] || "blue"}>{item.is_read ? "已读" : "未读"}</Tag>{item.title}</Space>}
                description={<><div>{item.content}</div><small>{new Date(item.created_at).toLocaleString("zh-CN")}</small></>}
              />
            </List.Item>
          )}
        />
      </Drawer>
      <Modal
        open={Boolean(selectedNotice)}
        title={selectedNotice?.title}
        footer={null}
        onCancel={() => setSelectedNotice(null)}
      >
        <Space wrap>
          <Tag color={colors[selectedNotice?.level || ""] || "blue"}>
            {selectedNotice?.is_read ? "已读" : "未读"}
          </Tag>
          <small>{selectedNotice?.created_at ? new Date(selectedNotice.created_at).toLocaleString("zh-CN") : ""}</small>
        </Space>
        <div style={{ marginTop: 16, whiteSpace: "pre-wrap" }}>{selectedNotice?.content}</div>
      </Modal>
    </>
  );
}
