import { useState } from "react";
import { Alert,Button,Card,Checkbox,DatePicker,Descriptions,Input,Select,Space,Tag,message } from "antd";
import { api } from "../../api";
import Table from "../../components/ResizableTable";
import dayjs from "dayjs";
import { isIprLawsuit,isLegacyIprRecord,personDisplayName } from "../constants";
import type { CpcApplication,IprRecord } from "../types";
import { ANNUAL_YEAR_OPTIONS,IPR_CASE_EDIT_FIELDS,IPR_CASE_FLAG_FIELDS,RELIEF_RATE_OPTIONS,iprCaseEditValues,iprCaseFlags,iprCaseInfoItems } from "./iprCaseInfo";

interface IprCaseDetailHeaderProps {
  detail: IprRecord;
  onOpenRebootCase: (caseId: number) => void;
  onSaved?: (record: IprRecord) => void;
}

export function IprCaseDetailHeader({ detail, onOpenRebootCase, onSaved }: IprCaseDetailHeaderProps) {
  if (!isIprLawsuit(detail)) return <IprCaseInfoGrid detail={detail} onOpenRebootCase={onOpenRebootCase} onSaved={onSaved} />;
  return (
    <>
      {isLegacyIprRecord(detail) ? (
        <Alert
          type="info"
          showIcon
          message="Historical IPR record: read-only"
          style={{ marginBottom: 12 }}
        />
      ) : null}
      <Descriptions
        bordered
        size="small"
        column={2}
        items={[
          {
            key: "serial",
            label: "案件编号",
            children: detail.serial_no,
          },
          { key: "status", label: "状态", children: detail.status },
          { key: "customer", label: "客户", children: detail.customer },
          {
            key: "application",
            label: "申请号/注册号",
            children: detail.data.application_no || "—",
          },
          ...(isIprLawsuit(detail)
            ? [
                {
                  key: "case-category",
                  label: "案件属性",
                  children: <Tag color="red">诉讼案件</Tag>,
                },
                {
                  key: "court-case-no",
                  label: "法院案号",
                  children: detail.data.court_case_no || "—",
                },
                {
                  key: "court",
                  label: "受理法院",
                  children: detail.data.court_name || "—",
                },
                {
                  key: "judge",
                  label: "承办法官 / 书记员",
                  children:
                    [detail.data.judge, detail.data.clerk]
                      .filter(Boolean)
                      .join(" / ") || "—",
                },
                {
                  key: "plaintiff",
                  label: "原告",
                  children: detail.data.plaintiff || "—",
                },
                {
                  key: "defendant",
                  label: "被告",
                  children: detail.data.defendant || "—",
                },
                {
                  key: "third-parties",
                  label: "第三人",
                  children: detail.data.third_parties || "—",
                },
              ]
            : [
                {
                  key: "case-category",
                  label: "案件属性",
                  children: <Tag>非诉案件</Tag>,
                },
              ]),
          {
            key: "type",
            label: "申请类型",
            children: detail.data.application_type || "—",
          },
          {
            key: "applicant",
            label: "申请人/权利人",
            children: detail.data.applicant || "—",
          },
          {
            key: "manager",
            label: "案件负责人",
            children: detail.data.case_manager || "—",
          },
          {
            key: "date",
            label: "申请日期",
            children: detail.data.application_date || "—",
          },
          {
            key: "deadline",
            label: "办理期限",
            children: detail.data.deadline || "—",
          },
          {
            key: "annual",
            label: "年费年度",
            children: detail.data.annual_fee_year || "—",
          },
          {
            key: "annual-monitoring",
            label: "年费监控",
            children: detail.data.annual_fee_monitoring ? (
              <Tag color="green">监控中</Tag>
            ) : (
              <Tag>未监控</Tag>
            ),
          },
          {
            key: "rate",
            label: "费率",
            children: detail.data.rate ?? "—",
          },
          {
            key: "reboot-source",
            label: "重提原案件",
            children: detail.data.reboot_source_case_id ? (
              <Button
                type="link"
                size="small"
                onClick={() => onOpenRebootCase(detail.data.reboot_source_case_id)}
              >
                {detail.data.reboot_source_case_no ||
                  detail.data.reboot_source_case_id}
              </Button>
            ) : (
              "—"
            ),
          },
          {
            key: "reboot-targets",
            label: "已重提案件",
            children:
              Array.isArray(detail.data.reboot_case_ids) &&
              detail.data.reboot_case_ids.length ? (
                <Space size={0} wrap>
                  {detail.data.reboot_case_ids.map(
                    (caseId: number, index: number) => (
                      <Button
                        key={caseId}
                        type="link"
                        size="small"
                        onClick={() => onOpenRebootCase(caseId)}
                      >
                        {detail.data.reboot_case_nos?.[index] || caseId}
                      </Button>
                    )
                  )}
                </Space>
              ) : (
                "—"
              ),
          },
          {
            key: "description",
            label: "说明",
            children: detail.description || "—",
            span: 2,
          },
        ]}
      />
    </>
  );
}


interface IprCpcPanelProps {
  detail: IprRecord;
  cpcApplications: CpcApplication[];
  cpcApplicationsLoading: boolean;
  cpcApplicationsError: string;
  cpcGenerating: boolean;
  onLoadCpcApplications: () => void;
  onGenerateCpcApplication: () => void;
  onDownloadCpcApplication: (application: CpcApplication) => void;
}

/** 专利案件的 CPC 申报，案件页里单独一个页签。 */
export function IprCpcPanel({ detail, cpcApplications, cpcApplicationsLoading, cpcApplicationsError, cpcGenerating, onLoadCpcApplications, onGenerateCpcApplication, onDownloadCpcApplication }: IprCpcPanelProps) {
  return (
        <Card
          size="small"
          title="CPC专利申报"
          extra={
            !isLegacyIprRecord(detail) ? (
              <Space>
                <Button
                  size="small"
                  onClick={onLoadCpcApplications}
                  loading={cpcApplicationsLoading}
                >
                  刷新历史
                </Button>
                <Button
                  size="small"
                  type="primary"
                  disabled={detail.status !== "在办"}
                  loading={cpcGenerating}
                  onClick={onGenerateCpcApplication}
                >
                  生成CPC申报文件
                </Button>
              </Space>
            ) : null
          }
        >
          <Alert
            type="info"
            showIcon
            message="生成CPC基础申报信息快照"
            description={`当前生成 ZIP 文件，内含 UTF-8 基础信息文本供核对；它不是中国专利电子申请系统的官方提交包。${
              detail.status === "在办"
                ? ""
                : " 仅在办案件可生成，历史文件仍可下载。"
            }`}
            style={{ marginBottom: 12 }}
          />
          {cpcApplicationsError ? (
            <Alert
              type="error"
              showIcon
              message={cpcApplicationsError}
              style={{ marginBottom: 12 }}
            />
          ) : null}
          <Table<CpcApplication>
            rowKey="id"
            size="small"
            loading={cpcApplicationsLoading}
            pagination={false}
            locale={{ emptyText: "暂无CPC申报记录" }}
            dataSource={cpcApplications}
            columns={[
              {
                title: "申报文件",
                dataIndex: "original_name",
                ellipsis: true,
              },
              {
                title: "格式",
                dataIndex: "format",
                width: 180,
                ellipsis: true,
              },
              {
                title: "状态",
                dataIndex: "status",
                width: 90,
                render: (value: string) => (
                  <Tag color="green">{value}</Tag>
                ),
              },
              {
                title: "生成人",
                dataIndex: "created_by",
                width: 100,
                render: personDisplayName,
              },
              {
                title: "生成时间",
                dataIndex: "created_at",
                width: 165,
                render: (value: string) =>
                  value
                    ? dayjs(value).format("YYYY-MM-DD HH:mm")
                    : "—",
              },
              {
                title: "操作",
                width: 80,
                render: (_, row) => (
                  <Button
                    type="link"
                    onClick={() => onDownloadCpcApplication(row)}
                  >
                    下载
                  </Button>
                ),
              },
            ]}
          />
        </Card>
  );
}

/** 非诉案件：按原系统案件页排成四列信息格，右侧一列是优先权等勾选项；右上角“修改/保存”（迁移案件也能改）。 */
function IprCaseInfoGrid({ detail, onOpenRebootCase, onSaved }: Pick<IprCaseDetailHeaderProps, "detail" | "onOpenRebootCase" | "onSaved">) {
  const rebootIds: number[] = Array.isArray(detail.data.reboot_case_ids) ? detail.data.reboot_case_ids : [];
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const [phaseOptions, setPhaseOptions] = useState<string[]>([]);
  const canEdit = detail.status !== "已结案";
  const startEdit = () => {
    setValues(iprCaseEditValues(detail));
    setFlags(Object.fromEntries(iprCaseFlags(detail).map((flag) => [flag.key, flag.checked])));
    setEditing(true);
    api.get<{ items: string[] }>(`/ipr/cases/${detail.id}/phase-options`)
      .then(({ data }) => setPhaseOptions(data.items || []))
      .catch(() => setPhaseOptions([]));
  };
  const save = async () => {
    const before = iprCaseEditValues(detail);
    const payload: Record<string, unknown> = {};
    for (const [key, config] of Object.entries(IPR_CASE_EDIT_FIELDS)) {
      if ((values[key] || "") === (before[key] || "")) continue;
      const value = (values[key] || "").trim();
      payload[config.field] = config.type === "annual-year" ? (value ? Number(value) : null)
        : config.type === "date" ? (value || null) : value;
    }
    for (const flag of iprCaseFlags(detail)) {
      if (Boolean(flags[flag.key]) !== flag.checked) payload[IPR_CASE_FLAG_FIELDS[flag.key]] = Boolean(flags[flag.key]);
    }
    if (!Object.keys(payload).length) { setEditing(false); return; }
    setSaving(true);
    try {
      const { data } = await api.patch<IprRecord>(`/ipr/cases/${detail.id}/info`, payload);
      message.success("案件信息已保存");
      setEditing(false);
      onSaved?.(data);
    } catch (failure: any) {
      message.error(failure?.response?.data?.detail || "案件信息保存失败");
    } finally {
      setSaving(false);
    }
  };
  const control = (key: string, shown: string) => {
    const config = IPR_CASE_EDIT_FIELDS[key];
    if (!editing || !config) return shown;
    const value = values[key] || "";
    const set = (next: string) => setValues((current) => ({ ...current, [key]: next }));
    if (config.type === "date") {
      return <DatePicker size="small" style={{ width: "100%" }} value={value ? dayjs(value) : null}
        onChange={(next) => set(next ? next.format("YYYY-MM-DD") : "")} />;
    }
    if (config.type === "phase" || config.type === "annual-year" || config.type === "relief-rate") {
      const options = config.type === "phase" ? phaseOptions.map((item) => ({ value: item, label: item }))
        : config.type === "annual-year" ? ANNUAL_YEAR_OPTIONS : RELIEF_RATE_OPTIONS;
      return <Select size="small" style={{ width: "100%" }} value={value || undefined} placeholder="请选择" allowClear
        options={options} onChange={(next) => set(next || "")} showSearch={config.type === "phase"} />;
    }
    return <Input size="small" value={value} onChange={(event) => set(event.target.value)} />;
  };
  return (
    <div className="ipr-case-info">
      <div className="ipr-case-info-tools">
        {editing ? (
          <Space size={8}>
            <Button size="small" onClick={() => setEditing(false)} disabled={saving}>取消</Button>
            <Button size="small" type="primary" loading={saving} onClick={() => void save()}>保存</Button>
          </Space>
        ) : canEdit ? <Button size="small" type="primary" onClick={startEdit}>修改</Button> : null}
      </div>
      <div className="ipr-case-info-body">
        <dl className="ipr-case-info-grid">
          {iprCaseInfoItems(detail).map((item) => (
            <div key={item.key} className={`ipr-case-info-cell ipr-case-info-${item.key}`}>
              <dt>{item.label}</dt>
              <dd title={editing ? undefined : item.value}>{control(item.key, item.value)}</dd>
            </div>
          ))}
          {detail.data.reboot_source_case_id || rebootIds.length ? (
            <div className="ipr-case-info-cell ipr-case-info-reboot">
              <dt>重提案件</dt>
              <dd>
                <Space size={0} wrap>
                  {detail.data.reboot_source_case_id ? (
                    <Button type="link" size="small" onClick={() => onOpenRebootCase(detail.data.reboot_source_case_id)}>
                      原案件 {detail.data.reboot_source_case_no || detail.data.reboot_source_case_id}
                    </Button>
                  ) : null}
                  {rebootIds.map((caseId, index) => (
                    <Button key={caseId} type="link" size="small" onClick={() => onOpenRebootCase(caseId)}>
                      {detail.data.reboot_case_nos?.[index] || caseId}
                    </Button>
                  ))}
                </Space>
              </dd>
            </div>
          ) : null}
        </dl>
        <ul className="ipr-case-info-flags">
          {iprCaseFlags(detail).map((flag) => (
            <li key={flag.key}>
              <Checkbox checked={editing ? Boolean(flags[flag.key]) : flag.checked} disabled={!editing || saving}
                onChange={(event) => setFlags((current) => ({ ...current, [flag.key]: event.target.checked }))}>{flag.label}</Checkbox>
            </li>
          ))}
        </ul>
      </div>
      {detail.description ? <p className="ipr-case-info-note">说明：{detail.description}</p> : null}
    </div>
  );
}
