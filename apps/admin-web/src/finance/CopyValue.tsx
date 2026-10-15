import { Button, message } from "antd";
import { CopyOutlined } from "@ant-design/icons";

export function CopyValue({ value, children }: { value?: unknown; children?: React.ReactNode }) {
  const text = String(value ?? "").trim();
  if (!text || text === "—") return <>{children ?? "—"}</>;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      message.success("已复制");
    } catch {
      message.error("复制失败，请手动选择文本复制");
    }
  };
  return <span className="finance-copy-value"><span>{children ?? text}</span><Button type="text" size="small" aria-label={`复制${text}`} icon={<CopyOutlined />} onClick={() => void copy()} /></span>;
}
