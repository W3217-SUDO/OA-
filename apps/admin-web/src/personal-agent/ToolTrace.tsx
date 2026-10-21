import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { Collapse } from "antd";
import type { ToolCallRecord } from "./types";

/** 本轮回答里智能体实际调用了哪些工具：名称、关键参数、结果和耗时，默认折叠。 */
export function ToolTrace({ trace }: { trace?: ToolCallRecord[] }) {
  if (!trace?.length) return null;
  const failed = trace.filter((item) => !item.ok).length;
  return (
    <Collapse
      className="workspace-tool-trace"
      size="small"
      ghost
      items={[{
        key: "trace",
        label: <span>本次调用了 {trace.length} 个工具{failed ? `，${failed} 个失败` : ""}</span>,
        children: (
          <ol className="workspace-tool-trace-list">
            {trace.map((item, index) => (
              <li key={`${item.name}-${index}`}>
                <span className={item.ok ? "is-ok" : "is-failed"}>{item.ok ? <CheckCircleOutlined /> : <CloseCircleOutlined />}</span>
                <strong>{item.label}</strong>
                {item.ms > 0 && <small>{item.ms >= 1000 ? `${(item.ms / 1000).toFixed(1)} 秒` : `${item.ms} 毫秒`}</small>}
                {item.detail && <code title={item.detail}>{item.detail}</code>}
              </li>
            ))}
          </ol>
        ),
      }]}
    />
  );
}
