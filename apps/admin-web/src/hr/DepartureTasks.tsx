import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Empty, Input, Modal, Space, Tag, message } from "antd";
import Table from "../components/ResizableTable";
import { KeywordPersonSelect, personKeywordMatches } from "../components/KeywordPersonSelect";
import { api } from "../api";
import { POPUP_WIDTH } from "../components/common/popupSize";

// 501631（tgn 11-05）：办离职/停用前，此人负责的未结束任务必须先转交；发起人、协作人的任务转交时一并换人。
// 已离职人员的存量任务由系统管理员在“离职人员未结束任务”清单里按人批量转交。

export type DepartureTask = {
  id: number; serial_no: string; title: string; status: string; owner: string; owner_name?: string;
  initiator: string; collaborators: string[]; case_no: string; deadline: string; task_type: string; legacy: boolean; roles: string[];
};
type Person = { value: string; label: string };

export const DEPARTURE_TASKS_BLOCKED = "未结束任务";
export const isDepartureTasksBlocked = (error: any) => String(error?.response?.data?.detail || "").includes(DEPARTURE_TASKS_BLOCKED);
const errorDetail = (error: any, fallback: string) => error?.response?.data?.detail || fallback;

function useActivePeople(exclude: string) {
  const [people, setPeople] = useState<Person[]>([]);
  useEffect(() => {
    api.get("/users/directory").then(({ data }) => {
      const items: any[] = Array.isArray(data) ? data : data?.items || [];
      setPeople(items.filter((item) => item.username && item.is_active !== false)
        .map((item) => ({ value: String(item.username), label: `${item.display_name || item.username}（${item.username}）` })));
    }).catch(() => setPeople([]));
  }, []);
  return useMemo(() => people.filter((item) => item.value !== exclude), [people, exclude]);
}

function TaskTable({ items, selected, onSelect }: { items: DepartureTask[]; selected: number[]; onSelect: (ids: number[]) => void }) {
  return (
    <Table<DepartureTask>
      rowKey="id" size="small" dataSource={items} scroll={{ x: 900 }}
      rowSelection={{ selectedRowKeys: selected, onChange: (keys) => onSelect(keys.map(Number)) }}
      pagination={{ defaultPageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
      locale={{ emptyText: <Empty description="没有未结束的任务" /> }}
      columns={[
        { title: "此人身份", dataIndex: "roles", width: 120, render: (roles: string[]) => roles.map((role) => <Tag key={role} color={role === "负责人" ? "red" : undefined}>{role}</Tag>) },
        { title: "任务编号", dataIndex: "serial_no", width: 150 },
        { title: "任务", dataIndex: "title", width: 220, ellipsis: true },
        { title: "案件", dataIndex: "case_no", width: 130 },
        { title: "状态", dataIndex: "status", width: 80 },
        { title: "负责人", dataIndex: "owner_name", width: 100, render: (value: string, row) => value || row.owner },
        { title: "截止日期", dataIndex: "deadline", width: 100 },
      ]}
    />
  );
}

function HandoverBar({ from, selected, onDone }: { from: string; selected: number[]; onDone: () => void }) {
  const people = useActivePeople(from);
  const [recipient, setRecipient] = useState<string>();
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const submit = async () => {
    if (!selected.length) { message.warning("请先勾选要转交的任务"); return; }
    if (!recipient) { message.warning("请选择接收人"); return; }
    setSaving(true);
    try {
      const { data } = await api.post("/hr/departure-tasks/handover", { from_username: from, task_ids: selected, recipient, comment });
      message.success(`已转交 ${data.updated} 条任务${data.owner_changed ? `，其中 ${data.owner_changed} 条负责人改为接收人，待其接收` : ""}`);
      onDone();
    } catch (error) {
      message.error(errorDetail(error, "批量转交失败"));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Space wrap style={{ marginTop: 8 }}>
      <KeywordPersonSelect aria-label="接收人" placeholder="选择接收人（可输入姓名或拼音首字母）" style={{ width: 280 }} allowClear showSearch
        value={recipient} onChange={(value) => setRecipient(value)} options={people}
        filterOption={(input, option) => personKeywordMatches(input, option?.label, option?.value)} />
      <Input placeholder="转交说明（选填）" style={{ width: 220 }} value={comment} maxLength={500} onChange={(event) => setComment(event.target.value)} />
      <Button type="primary" loading={saving} disabled={!selected.length} onClick={() => void submit()}>批量转交给此人（{selected.length}）</Button>
    </Space>
  );
}

/** 办离职/停用前的任务转交弹窗：列出此人名下未结束任务，勾选后批量转交；负责的任务转完才能继续办理。 */
export function DepartureHandoverModal({ username, name, action = "办理离职", onClose, onCleared }: {
  username: string | null; name?: string; action?: string; onClose: () => void; onCleared?: () => void;
}) {
  const [items, setItems] = useState<DepartureTask[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!username) return;
    setLoading(true);
    try {
      const { data } = await api.get<{ items: DepartureTask[] }>("/hr/departure-tasks", { params: { username } });
      setItems(data.items);
      setSelected(data.items.map((item) => item.id));
    } catch (error) {
      message.error(errorDetail(error, "未结束任务加载失败"));
    } finally {
      setLoading(false);
    }
  }, [username]);
  useEffect(() => { void load(); }, [load]);
  const ownerCount = items.filter((item) => item.roles.includes("负责人")).length;
  return (
    <Modal open={Boolean(username)} title={`${name || username || ""} 名下未结束的任务`} width={POPUP_WIDTH.xl} onCancel={onClose} destroyOnHidden
      footer={<Space>
        <Button onClick={onClose}>关闭</Button>
        {onCleared && <Button type="primary" disabled={loading || ownerCount > 0} onClick={onCleared}>继续{action}</Button>}
      </Space>}>
      {ownerCount > 0
        ? <Alert type="warning" showIcon style={{ marginBottom: 8 }} message={`此人还负责 ${ownerCount} 条未结束任务，转交给其他人后才能${action}。发起人、协作人的任务可一并勾选转交，不转也不影响办理。`} />
        : <Alert type="success" showIcon style={{ marginBottom: 8 }} message={items.length ? `负责的任务已全部转交，可以${action}；下面是此人作为发起人/协作人的任务，可一并转交。` : `此人名下没有未结束的任务，可以${action}。`} />}
      <div style={{ opacity: loading ? 0.5 : 1 }}>
        <TaskTable items={items} selected={selected} onSelect={setSelected} />
        {username && items.length > 0 && <HandoverBar from={username} selected={selected} onDone={() => void load()} />}
      </div>
    </Modal>
  );
}

type Group = { username: string; name: string; department: string; no_account: boolean; owner_count: number; total: number; items: DepartureTask[] };

/** 人事中心“离职人员未结束任务”：按人列出，系统管理员勾选后批量转交。 */
export function DepartedTasksPanel() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [current, setCurrent] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{ people: Group[] }>("/hr/departure-tasks");
      setGroups(data.people);
      setCurrent((value) => (data.people.some((group) => group.username === value) ? value : data.people[0]?.username || ""));
      setSelected([]);
    } catch (error) {
      message.error(errorDetail(error, "离职人员未结束任务加载失败"));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const shown = groups.filter((group) => !keyword.trim() || personKeywordMatches(keyword, group.name, group.username, group.department));
  const group = groups.find((item) => item.username === current);
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-start" }}>
      <Card size="small" title={`离职人员（${groups.length}）`} style={{ width: 260, flex: "0 0 260px" }} styles={{ body: { padding: "4px 0", maxHeight: 560, overflowY: "auto" } }}
        extra={<Button size="small" loading={loading} onClick={() => void load()}>刷新</Button>}>
        <div style={{ padding: "4px 8px" }}><Input allowClear size="small" placeholder="姓名/部门/拼音首字母" value={keyword} onChange={(event) => setKeyword(event.target.value)} /></div>
        {shown.map((item) => (
          <div key={item.username} role="button" tabIndex={0}
            onClick={() => { setCurrent(item.username); setSelected([]); }}
            onKeyDown={(event) => { if (event.key === "Enter") { setCurrent(item.username); setSelected([]); } }}
            style={{ padding: "5px 12px", cursor: "pointer", background: item.username === current ? "#e6f4ff" : undefined, color: item.username === current ? "#1677ff" : undefined }}>
            {item.name}{item.no_account ? "（无账号）" : ""}（负责 {item.owner_count}/共 {item.total}）
          </div>
        ))}
        {!shown.length && <Empty style={{ margin: 16 }} description={loading ? "加载中" : "没有离职人员的未结束任务"} />}
      </Card>
      <Card size="small" style={{ flex: "1 1 600px", minWidth: 0 }}
        title={group ? `${group.name}（${group.username}${group.department ? `，${group.department}` : ""}）名下未结束任务` : "未结束任务"}>
        {group ? <>
          <TaskTable items={group.items} selected={selected} onSelect={setSelected} />
          <HandoverBar from={group.username} selected={selected} onDone={() => void load()} />
        </> : <Empty description="请选择左侧人员" />}
      </Card>
    </div>
  );
}
