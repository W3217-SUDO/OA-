import { Alert,Button,Card,Checkbox,Descriptions,Space,Tag } from "antd";
import Table from "../../components/ResizableTable";
import dayjs from "dayjs";
import { isIprLawsuit,isLegacyIprRecord,personDisplayName } from "../constants";
import type { CpcApplication,IprRecord } from "../types";
import { iprCaseFlags,iprCaseInfoItems } from "./iprCaseInfo";

interface IprCaseDetailHeaderProps {
  detail: IprRecord;
  onOpenRebootCase: (caseId: number) => void;
}

export function IprCaseDetailHeader({ detail, onOpenRebootCase }: IprCaseDetailHeaderProps) {
  if (!isIprLawsuit(detail)) return <IprCaseInfoGrid detail={detail} onOpenRebootCase={onOpenRebootCase} />;
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

/** 非诉案件：按原系统案件页排成四列信息格，右侧一列是优先权等勾选项。 */
function IprCaseInfoGrid({ detail, onOpenRebootCase }: Pick<IprCaseDetailHeaderProps, "detail" | "onOpenRebootCase">) {
  const rebootIds: number[] = Array.isArray(detail.data.reboot_case_ids) ? detail.data.reboot_case_ids : [];
  return (
    <div className="ipr-case-info">
      {isLegacyIprRecord(detail) ? <Alert type="info" showIcon message="历史案件，只读" className="ipr-case-info-alert" /> : null}
      <div className="ipr-case-info-body">
        <dl className="ipr-case-info-grid">
          {iprCaseInfoItems(detail).map((item) => (
            <div key={item.key} className={`ipr-case-info-cell ipr-case-info-${item.key}`}>
              <dt>{item.label}</dt>
              <dd title={item.value}>{item.value}</dd>
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
            <li key={flag.key}><Checkbox checked={flag.checked} disabled>{flag.label}</Checkbox></li>
          ))}
        </ul>
      </div>
      {detail.description ? <p className="ipr-case-info-note">说明：{detail.description}</p> : null}
    </div>
  );
}
