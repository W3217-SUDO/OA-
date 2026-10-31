import { useEffect, useState } from "react";
import { Alert } from "antd";
import { api } from "../api";

// 审批人不再手选：按所属部门在人事中心“用印审批设置”里的审批路径自动带出（BUG20261031002 第④⑤步）。
type PathPreview = { path_display?: string[]; error?: string };

export default function ApprovalPathNotice({ recordId, department, withStamp = false }: { recordId?: number; department?: string; withStamp?: boolean }) {
  const [preview, setPreview] = useState<PathPreview | null>(null);
  useEffect(() => {
    let alive = true;
    void api.get<PathPreview>("/contracts/approval-path", { params: { record_id: recordId || undefined, department: department || undefined } })
      .then(({ data }) => { if (alive) setPreview(data); })
      .catch(() => { if (alive) setPreview({ error: "审批路径加载失败，提交时按所属部门自动带出" }); });
    return () => { alive = false; };
  }, [recordId, department]);
  if (!preview) return null;
  if (preview.error) return <Alert type="warning" showIcon title={preview.error} />;
  const steps = [...(preview.path_display || []), ...(withStamp ? ["行政用印"] : [])];
  return <Alert type="info" showIcon title={`审批路径：${steps.join(" → ")}`} description="按所属部门自动带出，不用选择审批人。" />;
}
