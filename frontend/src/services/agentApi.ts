import type { AgentCapability, AgentRun } from "../types/agent";

export async function getAgentCapabilities(): Promise<AgentCapability[]> {
  const response = await fetch("/api/v1/agent/capabilities");
  if (!response.ok) throw new Error(`Agent 能力加载失败: ${response.status}`);
  const data = (await response.json()) as { items: AgentCapability[] };
  return data.items;
}

export async function runAgent(skill: string, input: string): Promise<AgentRun> {
  const response = await fetch("/api/v1/agent/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ skill, input, context: { source: "vue-demo" } }),
  });
  if (!response.ok) throw new Error(`Agent 执行失败: ${response.status}`);
  return (await response.json()) as AgentRun;
}

