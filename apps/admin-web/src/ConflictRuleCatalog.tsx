import { useEffect, useState } from "react";
import { Alert, Button, Card, Select, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";

import { api } from "./api";
import type { ConflictAutoReviewStatus } from "./system/types";

type ConflictRule = {
  id: string;
  category: string;
  title: string;
  outcome_if_confirmed: "BLOCK" | "WAIVER_REQUIRED" | "SPECIAL";
  legal_basis: string;
  trigger: string;
  required_facts: string[];
  manual_boundary: string;
  branches?: Array<{ condition: string; action: string; description: string }>;
};

type ConflictRuleCatalogResponse = {
  version: string;
  source_title: string;
  legal_source: string;
  legal_source_url: string;
  policy_status: "PENDING_CONFIRMATION";
  automation_status: "MANUAL_REVIEW_ONLY";
  auto_review: ConflictAutoReviewStatus;
  rules: ConflictRule[];
};

const categoryNames: Record<string, string> = {
  A: "律师本人及近亲属",
  B: "本所其他人员",
  C: "律师既往履历",
  D: "同一律师的不同委托",
  E: "全所的不同委托",
  F: "破产管理人专项",
};

const columns: ColumnsType<ConflictRule> = [
  { title: "编号", dataIndex: "id", width: 95 },
  { title: "类别", dataIndex: "category", width: 145, render: (value: string) => categoryNames[value] || value },
  { title: "规则情形", dataIndex: "title", className: "conflict-rule-title" },
  {
    title: "确认命中后",
    dataIndex: "outcome_if_confirmed",
    width: 130,
    render: (value: ConflictRule["outcome_if_confirmed"]) => (
      <Tag color={value === "BLOCK" ? "red" : value === "WAIVER_REQUIRED" ? "gold" : "blue"}>
        {value === "BLOCK" ? "绝对禁止" : value === "WAIVER_REQUIRED" ? "相对禁止" : "专项分情形处理"}
      </Tag>
    ),
  },
  { title: "依据", dataIndex: "legal_basis", width: 275 },
];

export default function ConflictRuleCatalog() {
  const [catalog, setCatalog] = useState<ConflictRuleCatalogResponse | null>(null);
  const [category, setCategory] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    api.get<ConflictRuleCatalogResponse>("/conflict-rules", { signal: controller.signal })
      .then(({ data }) => setCatalog(data))
      .catch((requestError: any) => {
        if (requestError?.code === "ERR_CANCELED") return;
        setCatalog(null);
        setError(requestError?.response?.data?.detail || "规则目录加载失败，请重试。");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reloadKey]);

  const visibleRules = catalog?.rules.filter((rule) => category === "ALL" || rule.category === category) || [];
  const autoReview = catalog?.auto_review;
  const statusAvailable = Boolean(autoReview && typeof autoReview.effective === "boolean");

  return (
    <Card className="panel conflict-rules-panel" title="利益冲突审查规则">
      <Alert
        type={!statusAvailable ? error ? "error" : "info" : autoReview?.effective ? "success" : "warning"}
        showIcon
        message={!statusAvailable ? error ? "自动利冲审查状态不可用" : "正在读取自动利冲审查状态" : autoReview?.effective ? "自动利冲审查运行中" : "规则目录供人工审查参考，自动利冲审查未运行"}
        description={`${statusAvailable ? autoReview?.reason || "" : ""} 现有名称/证件号检索仅显示历史匹配，不代表利益冲突审查通过；身份、同案关系或证据不明时须人工核实。`}
      />
      {error && (
        <Alert
          className="conflict-rule-error"
          type="error"
          showIcon
          message={error}
          action={<Button size="small" onClick={() => setReloadKey((value) => value + 1)}>重试</Button>}
        />
      )}
      {catalog && (
        <>
          <div className="conflict-rule-toolbar">
            <span>版本：{catalog.version} · 共 {catalog.rules.length} 条 · 待业务确认</span>
            <Select
              aria-label="按类别筛选利冲规则"
              value={category}
              onChange={setCategory}
              options={[
                { value: "ALL", label: "全部类别" },
                ...Object.entries(categoryNames).map(([value, label]) => ({ value, label })),
              ]}
            />
          </div>
          <Table<ConflictRule>
            size="small"
            rowKey="id"
            columns={columns}
            dataSource={visibleRules}
            loading={loading}
            pagination={{ pageSize: 10, showSizeChanger: false }}
            scroll={{ x: 800 }}
            expandable={{
              expandedRowRender: (rule) => (
                <div className="conflict-rule-details">
                  <p><strong>检查时点：</strong>{rule.trigger}</p>
                  <p><strong>所需事实：</strong>{rule.required_facts.join("、")}</p>
                  <p><strong>人工核查边界：</strong>{rule.manual_boundary}</p>
                  {rule.branches?.map((branch) => (
                    <p key={branch.action}><strong>{branch.condition}：</strong>{branch.description}</p>
                  ))}
                </div>
              ),
              rowExpandable: () => true,
            }}
          />
          <div className="conflict-rule-source">
            来源：{catalog.source_title}；
            <a href={catalog.legal_source_url} target="_blank" rel="noopener noreferrer">{catalog.legal_source}</a>
          </div>
        </>
      )}
    </Card>
  );
}
