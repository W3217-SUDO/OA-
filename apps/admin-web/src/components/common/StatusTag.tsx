import { Tag } from "antd";
import type { ReactNode } from "react";
import { STATUS_TONE_COLOR, statusToneOf, type StatusTone } from "./statusTone";

type StatusTagProps = {
  /** 存储的状态值，用来查颜色 */
  status: unknown;
  /** 显示文字与存储值不同时传入，例如用印把“待审批”显示成“待审核” */
  label?: ReactNode;
  /** 个别场景需要偏离总表时显式指定含义 */
  tone?: StatusTone;
  /** 总表里查不到时：默认按“已终止”灰色；案件阶段这类列传 "stage" 按阶段标签显示 */
  fallback?: "neutral" | "stage";
};

/** 全站统一的状态标签，颜色只来自 statusTone.ts。 */
export function StatusTag({ status, label, tone, fallback = "neutral" }: StatusTagProps) {
  const text = label ?? (status == null || status === "" ? "—" : String(status));
  const resolved = tone ?? statusToneOf(status);
  if (!resolved && fallback === "stage") return <StageTag>{text}</StageTag>;
  return <Tag color={STATUS_TONE_COLOR[resolved ?? "neutral"]}>{text}</Tag>;
}

/** 诉讼阶段等流程阶段：统一的浅色描边标签，不按阶段区分颜色。 */
export function StageTag({ children }: { children: ReactNode }) {
  return <Tag variant="outlined">{children}</Tag>;
}
