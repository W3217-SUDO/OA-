import { useEffect, useState } from "react";
import { Alert, Form } from "antd";
import type { FormInstance } from "antd";
import { api } from "../api";

export function CustomerPartyConflictHint({ form }: { form: FormInstance }) {
  const name = Form.useWatch("title", form);
  const code = Form.useWatch("credit_code", form);
  const [result, setResult] = useState<{ matched: boolean; historical_pending: boolean; message: string } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setResult(null); setError("");
    if (!String(name || "").trim()) return;
    const timer = window.setTimeout(() => {
      void api.get("/customers/party-directory/check", { params: { name: String(name).trim(), credit_code: code || "" } }).then(({ data }) => {
        if (typeof data.matched !== "boolean" || typeof data.historical_pending !== "boolean") throw new Error("对手方核查响应无效");
        if (active) setResult(data);
      }).catch(cause => { if (active) setError(cause.response?.data?.detail || cause.message || "对手方核查失败"); });
    }, 500);
    return () => { active = false; window.clearTimeout(timer); };
  }, [name, code]);
  if (error) return <Alert type="error" showIcon title={`对手方身份尚未完成核查：${error}`} />;
  if (!result) return null;
  return <Alert style={{ marginBottom: 12 }} type={result.matched ? "warning" : "info"} showIcon title={result.message}
    description={result.historical_pending ? "部分历史案件尚未分类，此提示不能替代完整的利益冲突审查或作为无冲突结论。" : "身份匹配提示供核实，正式审查仍通过现有利益冲突流程办理。"} />;
}
