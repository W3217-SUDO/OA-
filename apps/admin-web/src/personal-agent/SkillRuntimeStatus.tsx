import { Tag } from "antd";
import type { SkillRuntime } from "./types";
import "./skill-runtime-status.css";

export function SkillRuntimeStatus({ runtime, enabled, details = false }: { runtime?: SkillRuntime; enabled?: boolean; details?: boolean }) {
  if (!runtime) return null;
  const disabled = enabled === false;
  const label = disabled ? "已停用" : !runtime.ready ? runtime.missing_dependencies.length ? "依赖未就绪" : "资源未就绪" : runtime.mode === "script" ? "DSH 可调用" : "指令技能";
  const color = disabled ? "default" : !runtime.ready ? "warning" : "success";
  return <div className="skill-runtime-status" aria-label="技能运行状态">
    <Tag color={color}>{label}</Tag>
    {details && <div className="skill-runtime-description">
      <span>{runtime.mode === "script" ? "DSH 原生脚本技能" : "DSH 指令技能"} · {runtime.resource_count} 个资源文件</span>
      {runtime.message && <p>{runtime.message}</p>}
      {!!runtime.missing_dependencies.length && <p>缺少依赖：{runtime.missing_dependencies.join("、")}</p>}
    </div>}
  </div>;
}
