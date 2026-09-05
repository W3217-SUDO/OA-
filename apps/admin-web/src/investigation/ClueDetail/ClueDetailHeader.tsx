import { Descriptions, Button, Tag } from "antd";
import { statusColors } from "../constants";
import type { Row } from "../types";

interface ClueDetailHeaderProps {
  investigationDetail: Row | null;
  projectedPersonDisplayName: (displayName: unknown, username: unknown) => string;
  onOpenLinkedCustomer: (name: string) => void;
  onOpenLinkedInvestigation: (serialNo: string, module: "investigation" | "clue" | "task") => void;
  onOpenLinkedCase: (caseNo: string) => void;
  onOpenLinkedNotary: (recordId?: number, certificateNo?: string) => void;
}

export default function ClueDetailHeader({
  investigationDetail,
  projectedPersonDisplayName,
  onOpenLinkedCustomer,
  onOpenLinkedInvestigation,
  onOpenLinkedCase,
  onOpenLinkedNotary,
}: ClueDetailHeaderProps) {
  const investigationDetailItems = investigationDetail
    ? [
        {
          key: "no",
          label: "调查编号",
          children: investigationDetail.serial_no,
        },
        {
          key: "status",
          label: "状态",
          children: (
            <Tag color={statusColors[investigationDetail.status] || "blue"}>
              {investigationDetail.status}
            </Tag>
          ),
        },
        {
          key: "title",
          label: "调查事项",
          children: investigationDetail.title,
          span: 2,
        },
        {
          key: "customer",
          label: "权利人",
          children: investigationDetail.customer ? (
            <Button
              className="business-relation-link"
              type="link"
              onClick={() =>
                void onOpenLinkedCustomer(investigationDetail.customer)
              }
            >
              {investigationDetail.customer}
            </Button>
          ) : (
            "—"
          ),
        },
        {
          key: "right-type",
          label: "权利类型",
          children: investigationDetail.data.right_type || "—",
        },
        {
          key: "owner",
          label: "调查员",
          children: projectedPersonDisplayName(
            investigationDetail.owner_display_name,
            investigationDetail.owner,
          ),
        },
        {
          key: "region",
          label: "调查区域",
          children: investigationDetail.data.region || [investigationDetail.data.province, investigationDetail.data.city, investigationDetail.data.district].filter(Boolean).join(" ") || "—",
        },
        {
          key: "started-at",
          label: "开始时间",
          children: investigationDetail.data.started_at || investigationDetail.data.start_date || investigationDetail.data.authorized_from || "—",
        },
        {
          key: "ended-at",
          label: "结束时间",
          children: investigationDetail.data.ended_at || investigationDetail.data.end_date || investigationDetail.data.deadline || investigationDetail.data.authorized_to || "—",
        },
        {
          key: "source-owner",
          label: "案源人",
          children: projectedPersonDisplayName(
            investigationDetail.data.source_owner_display_name,
            investigationDetail.data.source_owner,
          ),
        },
        {
          key: "assigner",
          label: "任务分配人",
          children:
            projectedPersonDisplayName(
              investigationDetail.data.assigner_display_name ||
                investigationDetail.data.assigned_by_display_name,
              investigationDetail.data.assigner ||
                investigationDetail.data.assigned_by,
            ),
        },
        ...((investigationDetail.data.parent_task_no || investigationDetail.data.investigation_no)
          ? [{
              key: "parent-investigation",
              label: "父调查编号",
              children: <Button className="business-relation-link" type="link" onClick={() => void onOpenLinkedInvestigation(String(investigationDetail.data.parent_task_no || investigationDetail.data.investigation_no), investigationDetail.data.parent_task_no ? "task" : "investigation")}>
                {String(investigationDetail.data.parent_task_no || investigationDetail.data.investigation_no)}
              </Button>,
            }]
          : []),
        ...(investigationDetail.data.source_task_no
          ? [
              {
                key: "source-task",
                label: "来源调查任务",
                children: (
                  <Button
                    className="business-relation-link"
                    type="link"
                    onClick={() =>
                      onOpenLinkedInvestigation(
                        String(investigationDetail.data.source_task_no),
                        "task",
                      )
                    }
                  >
                    {String(investigationDetail.data.source_task_no)}
                  </Button>
                ),
              },
            ]
          : []),
        ...(investigationDetail.data.clue_no
          ? [
              {
                key: "clue",
                label: "关联线索",
                children: (
                  <Button
                    className="business-relation-link"
                    type="link"
                    onClick={() =>
                      onOpenLinkedInvestigation(
                        String(investigationDetail.data.clue_no),
                        "clue",
                      )
                    }
                  >
                    {String(investigationDetail.data.clue_no)}
                  </Button>
                ),
              },
            ]
          : []),
        ...(investigationDetail.data.case_no ||
        investigationDetail.data.converted_case_no
          ? [
              {
                key: "case",
                label: "关联案件",
                children: (
                  <Button
                    className="business-relation-link"
                    type="link"
                    onClick={() =>
                      void onOpenLinkedCase(
                        String(
                          investigationDetail.data.case_no ||
                            investigationDetail.data.converted_case_no,
                        ),
                      )
                    }
                  >
                    {String(
                      investigationDetail.data.case_no ||
                        investigationDetail.data.converted_case_no,
                    )}
                  </Button>
                ),
              },
            ]
          : []),
        ...(investigationDetail.data.certificate_no ||
        investigationDetail.data.notary_record_id
          ? [
              {
                key: "notary",
                label: "关联公证",
                children: (
                  <Button
                    className="business-relation-link"
                    type="link"
                    onClick={() =>
                      void onOpenLinkedNotary(
                        investigationDetail.data.notary_record_id,
                        investigationDetail.data.certificate_no,
                      )
                    }
                  >
                    {String(
                      investigationDetail.data.certificate_no ||
                        `公证ID：${investigationDetail.data.notary_record_id}`,
                    )}
                  </Button>
                ),
              },
            ]
          : []),
        ...(investigationDetail.module === "clue"
          ? [
              {
                key: "infringement",
                label: "侵权方式",
                children:
                  investigationDetail.data.infringement_method ||
                  "—",
              },
              {
                key: "sales-channel",
                label: "销售渠道",
                children:
                  investigationDetail.data.sales_channel ||
                  investigationDetail.data.platform ||
                  "—",
              },
              {
                key: "investigated-at",
                label: "调查日期",
                children: investigationDetail.data.investigated_at || "—",
              },
              {
                key: "store-url",
                label: "店铺链接",
                children: investigationDetail.data.store_url ? (
                  <a
                    href={String(investigationDetail.data.store_url)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {String(investigationDetail.data.store_url)}
                  </a>
                ) : (
                  "—"
                ),
              },
              {
                key: "shop-name",
                label: "店铺名称",
                children: investigationDetail.data.shop_name || investigationDetail.title || "—",
              },
              {
                key: "shop-id",
                label: "店铺Id",
                children: investigationDetail.data.shop_id || "—",
              },
              {
                key: "has-product",
                label: "有无产品",
                children: investigationDetail.data.has_product ? "有" : "无",
              },
              {
                key: "address",
                label: "调查地址",
                children: investigationDetail.data.address || "—",
              },
              {
                key: "platform",
                label: "调查平台",
                children: investigationDetail.data.platform || "—",
              },
              {
                key: "product",
                label: "侵权产品",
                children: investigationDetail.data.product || "—",
              },
              {
                key: "source",
                label: "来源",
                children: investigationDetail.data.source || "—",
              },
              {
                key: "producer",
                label: "生产商",
                children:
                  investigationDetail.data.producer ||
                  investigationDetail.data.producers ||
                  "—",
              },
              {
                key: "indictee",
                label: "主体信息",
                children:
                  investigationDetail.data.indictee ||
                  investigationDetail.data.indictees ||
                  investigationDetail.data.subject ||
                  "—",
              },
              {
                key: "assistant",
                label: "调查辅助",
                children:
                  projectedPersonDisplayName(
                    investigationDetail.data.investigation_assistant_display_name,
                    investigationDetail.data.investigation_assistant ||
                      investigationDetail.data.assistant,
                  ),
              },
              {
                key: "collected-at",
                label: "取证日期",
                children: investigationDetail.data.collected_at || "—",
              },
              {
                key: "notary-institution",
                label: "取证机构",
                children: investigationDetail.data.notary_institution || "—",
              },
              {
                key: "certificate-no",
                label: "公证书号",
                children: investigationDetail.data.certificate_no || "—",
              },
              {
                key: "invoice-no",
                label: "发票号",
                children: investigationDetail.data.invoice_no || "—",
              },
              {
                key: "warehouse",
                label: "证物存放处",
                children:
                  investigationDetail.data.warehouse ||
                  investigationDetail.data.certificate_storage_location ||
                  "—",
              },
              {
                key: "evidence-status",
                label: "证物状态",
                children:
                  investigationDetail.data.evidence_status ||
                  investigationDetail.data.warehouse_status ||
                  investigationDetail.data.storage_status ||
                  "—",
              },
              {
                key: "investigator-remark",
                label: "调查员备注",
                children: investigationDetail.data.investigator_remark || "—",
              },
              {
                key: "review-remark",
                label: "审批备注",
                children: investigationDetail.data.review_comment || "—",
              },
              {
                key: "customer-review-remark",
                label: "客户审核备注",
                children:
                  investigationDetail.data.customer_review_comment || "—",
              },
            ]
          : []),
        {
          key: "description",
          label: "说明",
          children: investigationDetail.description || "—",
          span: 2,
        },
      ]
    : [];

  return (
    <Descriptions
      bordered
      size="small"
      column={2}
      items={investigationDetailItems}
    />
  );
}
