import { useRef, useState } from "react";
import { Button, Card, Input, Table, message } from "antd";
import { api } from "./api";
import "./customer-conflict.css";

type ConflictSearchResult = {
  query: string;
  found: boolean;
  enterprise_name: string;
  latest_case_no: string;
  latest_case_date: string;
  plaintiffs: string[];
  defendants: string[];
  third_parties: string[];
  our_customer: string;
  customer_managers: string[];
  matches?: Array<{case_no:string;case_date:string;our_customer:string;plaintiffs:string[];defendants:string[];third_parties:string[];match_reason:string;relation_path:string[]}>;
};

const enterpriseFields: Array<{
  key: Exclude<keyof ConflictSearchResult, "query" | "found" | "matches">;
  label: string;
}> = [
  { key: "enterprise_name", label: "企业名称" },
  { key: "latest_case_no", label: "最新立案号" },
  { key: "latest_case_date", label: "最新立案日期" },
  { key: "plaintiffs", label: "原告" },
  { key: "defendants", label: "被告" },
  { key: "third_parties", label: "第三人" },
  { key: "our_customer", label: "我方客户" },
  { key: "customer_managers", label: "客户管理人" },
];

const displayValue = (
  key: Exclude<keyof ConflictSearchResult, "query" | "found" | "matches">,
  value: string | string[],
) => {
  const text = Array.isArray(value) ? value.join(",") : value || "";
  if (key !== "latest_case_date") return text;
  return text.replace(
    /^(\d{4})-0?(\d{1,2})-0?(\d{1,2})$/,
    (_match, year, month, day) => `${year}-${Number(month)}-${Number(day)}`,
  );
};

export default function CustomerConflictPage() {
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ConflictSearchResult | null>(null);
  const requestSequence = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);

  const search = async () => {
    const query = name.trim();
    activeRequest.current?.abort();
    const sequence = requestSequence.current + 1;
    requestSequence.current = sequence;
    setResult(null);
    if (!query) {
      activeRequest.current = null;
      setLoading(false);
      message.warning("请输入企业名称。");
      return;
    }
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    try {
      const { data } = await api.get<ConflictSearchResult>(
        "/customers/conflicts",
        { params: { name: query }, signal: controller.signal },
      );
      if (requestSequence.current === sequence) setResult(data);
    } catch (error: any) {
      if (
        requestSequence.current === sequence &&
        error?.code !== "ERR_CANCELED"
      ) {
        setResult(null);
        message.error(error?.response?.data?.detail || "检索失败");
      }
    } finally {
      if (requestSequence.current === sequence) {
        activeRequest.current = null;
        setLoading(false);
      }
    }
  };

  const foundItem = result?.found ? result : null;

  return (
    <Card className="panel conflict-panel" title="客户利益冲突检索">
      <div className="conflict-steps" aria-label="检索步骤">
        <div className={foundItem ? "" : "active"}>
          1.输入当事人名称或证件号
        </div>
        <div className={foundItem ? "active" : ""}>2.企业信息</div>
      </div>
      <div className="conflict-tip">
        可使用完整当事人名称、身份证号或统一社会信用代码检索。
      </div>

      {foundItem ? (
        <><div className="conflict-enterprise-grid">
          {enterpriseFields.map((field) => (
            <div className="conflict-enterprise-field" key={field.key}>
              <label>{field.label}：</label>
              <Input
                readOnly
                value={displayValue(field.key, foundItem[field.key])}
              />
            </div>
          ))}
        </div>
        <Table size="small" rowKey="case_no" pagination={{pageSize:10}} dataSource={foundItem.matches || []} columns={[
          {title:"案件编号",dataIndex:"case_no"},
          {title:"立案日期",dataIndex:"case_date"},
          {title:"我方客户",dataIndex:"our_customer"},
          {title:"命中依据",dataIndex:"match_reason"},
          {title:"关系路径",dataIndex:"relation_path",render:(value:string[])=>value.join(" → ")},
          {title:"原告",dataIndex:"plaintiffs",render:(value:string[])=>value.join("、")},
          {title:"被告",dataIndex:"defendants",render:(value:string[])=>value.join("、")},
        ]} scroll={{x:980}} />
        </>
      ) : (
        <div className="conflict-search-box">
          <div className="conflict-search">
            <label>名称/证件号：</label>
            <Input
              value={name}
              onChange={(event) => {
                setName(event.target.value);
              }}
            />
            <Button loading={loading} onClick={search}>
              <span>检索</span>
            </Button>
          </div>
          {result && !result.found && (
            <div className="conflict-not-found">
              未找到该企业基本信息.
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
