import { useEffect, useState } from "react";
import { Alert, Spin } from "antd";
import { api } from "../api";

type Bundle = {
  clue: { serial_no: string; title?: string };
  evidences: Array<{ id: number; serial_no: string; certificate_no?: string; location?: string }>;
  fees: Array<{ id: number; serial_no: string; title: string; amount?: number | string }>;
};

/** 移动前列出这条线索会一起带走的证物（公证书号、仓库位置）和费用（501337）。 */
export function ClueBundlePreview({ caseId, clueId }: { caseId?: number; clueId?: number }) {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!caseId || !clueId) { setBundle(null); return; }
    let alive = true;
    setLoading(true);
    setError("");
    api.get(`/cases/${caseId}/clues/${clueId}/bundle`)
      .then(({ data }) => { if (alive) setBundle(data); })
      .catch((reason) => { if (alive) setError(reason?.response?.data?.detail || "线索资料加载失败"); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [caseId, clueId]);
  if (!caseId || !clueId) return null;
  if (loading) return <Spin size="small" />;
  if (error) return <Alert type="error" showIcon message={error} />;
  if (!bundle) return null;
  return <Alert type="info" showIcon data-testid="clue-bundle-preview" message={`线索 ${bundle.clue.serial_no} 将连同以下内容一起移过去`} description={<div>
    <div>证物：{bundle.evidences.length ? bundle.evidences.map((item) => `${item.certificate_no || item.serial_no}${item.location ? `（${item.location}）` : ""}`).join("、") : "无"}</div>
    <div>费用：{bundle.fees.length ? bundle.fees.map((item) => `${item.title} ${item.amount ?? ""}`.trim()).join("、") : "无"}</div>
  </div>} />;
}
