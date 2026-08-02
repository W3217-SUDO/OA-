import { useRef, useState } from "react";
import { Button, Card, Input, message } from "antd";
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
};

const enterpriseFields: Array<{
  key: Exclude<keyof ConflictSearchResult, "query" | "found">;
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
  key: Exclude<keyof ConflictSearchResult, "query" | "found">,
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
    const controller = new AbortController();
    activeRequest.current = controller;
    const sequence = requestSequence.current + 1;
    requestSequence.current = sequence;
    setResult(null);
    setLoading(true);
    try {
      const { data } = await api.get<ConflictSearchResult>(
        "/customers/conflicts",
        { params: query ? { name: query } : {}, signal: controller.signal },
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
          1.输入完整企业名称
        </div>
        <div className={foundItem ? "active" : ""}>2.企业信息</div>
      </div>
      <div className="conflict-tip">
        温馨提示 ： 1. 需要输入完整的企业名称，才能查看具体信息.
      </div>

      {foundItem ? (
        <div className="conflict-enterprise-grid">
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
      ) : (
        <div className="conflict-search-box">
          <div className="conflict-search">
            <label>企业名称：</label>
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
