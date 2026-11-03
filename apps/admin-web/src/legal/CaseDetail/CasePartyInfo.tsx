import { Alert, Button, Descriptions, Empty, Modal, Space, Spin, Tag, message } from "antd";
import { Fragment, useEffect, useState } from "react";
import { api } from "../../api";
import { POPUP_WIDTH } from "../../components/common/popupSize";
import { errorText } from "../../personal-agent/types";

type Row = { label: string; value: string };
type PartyInfo = {
  name: string; role: string; person: boolean;
  identity: { organization_type: string; identity_no: string };
  local: { kind: string; id: number; serial_no: string; rows: Row[] }[];
  business: { rows: Row[]; queried_at: string; abnormal: boolean } | null;
};

/** 原告、被告、第三人名称拆成单个名字（和后端 case_parties._names 一致）。 */
export function casePartyNames(value: unknown): string[] {
  const items = Array.isArray(value) ? value : String(value ?? "").split(/[、，,]/);
  return items.map((item) => (typeof item === "string" ? item.trim() : "")).filter((item) => item && item !== "—");
}

/** 案件信息里的当事人名称可点开（501226，陶国南 11-03）。 */
export function CasePartyLinks({ caseId, names }: { caseId: number; names: string[] }) {
  const [opened, setOpened] = useState("");
  if (!names.length) return <>—</>;
  return <>
    {names.map((name, index) => <Fragment key={name}>
      {index > 0 && "、"}
      <Button type="link" className="case-cell-link" onClick={() => setOpened(name)}>{name}</Button>
    </Fragment>)}
    {opened && <CasePartyInfoModal caseId={caseId} name={opened} onClose={() => setOpened("")} />}
  </>;
}

const time = (value: string) => value ? new Date(value).toLocaleString("zh-CN") : "";
const rowsView = (rows: Row[]) => <Descriptions size="small" column={1} bordered
  items={rows.map((row) => ({ key: row.label, label: row.label, children: <span style={{ whiteSpace: "pre-wrap" }}>{row.value}</span> }))} />;

function CasePartyInfoModal({ caseId, name, onClose }: { caseId: number; name: string; onClose: () => void }) {
  const [info, setInfo] = useState<PartyInfo | null>(null);
  const [error, setError] = useState("");
  const [querying, setQuerying] = useState(false);
  useEffect(() => {
    api.get<PartyInfo>(`/cases/${caseId}/parties/info`, { params: { name } })
      .then(({ data }) => setInfo(data)).catch((failure) => setError(errorText(failure, "当事人信息读取失败")));
  }, [caseId, name]);
  const query = async (refresh: boolean) => {
    setQuerying(true);
    try {
      const { data } = await api.post<PartyInfo>(`/cases/${caseId}/parties/business-info`, { name, refresh });
      setInfo(data); message.success("工商信息已更新");
    } catch (failure) { message.error(errorText(failure, "查询工商信息失败")); }
    finally { setQuerying(false); }
  };
  const [saving, setSaving] = useState("");
  const saveDocument = async (kind: "basic" | "due_diligence") => {
    setSaving(kind);
    try {
      const { data } = await api.post<{ file: { original_name?: string; name?: string } }>(`/cases/${caseId}/parties/documents`, { name, kind });
      message.success(`已存到案件空间：${data.file.original_name || data.file.name || ""}`);
    } catch (failure) { message.error(errorText(failure, "生成失败")); }
    finally { setSaving(""); }
  };
  const confirmRefresh = () => Modal.confirm({
    title: "重新查询工商信息？", content: "会再调用一次企查查企业工商信息接口，计费 0.20 元。", okText: "重新查询", cancelText: "取消",
    onOk: () => query(true),
  });
  return <Modal open title={`当事人信息：${name}`} onCancel={onClose} footer={null} width={POPUP_WIDTH.md} destroyOnHidden>
    {error && <Alert type="error" showIcon title={error} />}
    {!info && !error && <Spin />}
    {info && <Space orientation="vertical" size={16} style={{ width: "100%" }}>
      <Space wrap>
        <Tag color="blue">{info.role}</Tag>
        {info.identity.organization_type && <Tag>{info.identity.organization_type}</Tag>}
        {info.identity.identity_no && <span>{info.person ? "身份证号" : "统一社会信用代码"}：{info.identity.identity_no}</span>}
      </Space>
      <div>
        <h4>系统资料</h4>
        {info.local.length ? info.local.map((item) => <div key={`${item.kind}-${item.id}`} style={{ marginBottom: 8 }}>
          <div style={{ marginBottom: 4 }}>{item.kind} {item.serial_no}</div>
          {item.rows.length ? rowsView(item.rows) : <span>暂无其他资料</span>}
        </div>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="客户和当事人库里没有这个名称" />}
      </div>
      {!info.person && <div>
        <Space wrap style={{ marginBottom: 4 }}>
          <h4 style={{ margin: 0 }}>工商信息（企查查）</h4>
          {info.business?.abnormal && <Tag color="error">登记状态异常</Tag>}
          {info.business
            ? <Button size="small" loading={querying} onClick={confirmRefresh}>重新查询</Button>
            : <Button size="small" type="primary" loading={querying} onClick={() => void query(false)}>查询工商信息</Button>}
        </Space>
        {info.business
          ? <>{rowsView(info.business.rows)}<div style={{ marginTop: 4, color: "#888" }}>查询时间 {time(info.business.queried_at)}，以后查看不再计费</div>
            <Space wrap style={{ marginTop: 12 }}>
              <Button loading={saving === "basic"} onClick={() => void saveDocument("basic")}>保存{info.role}基本信息到案件空间</Button>
              <Button loading={saving === "due_diligence"} onClick={() => void saveDocument("due_diligence")}>生成尽职调查报告</Button>
            </Space></>
          : <Alert type="info" showIcon title="还没有查过。点“查询工商信息”会调用一次企查查企业工商信息接口（0.20 元），查到后存进系统，以后谁再看都不再计费。" />}
      </div>}
    </Space>}
  </Modal>;
}
