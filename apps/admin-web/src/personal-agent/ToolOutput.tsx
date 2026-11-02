/** 外部MCP工具的原始返回（第三方内容）：默认折叠，点开查看；智能体会接着整理成回答。 */
export function ToolOutput({ content }: { content: string }) {
  return <details className="agent-tool-output">
    <summary>外部服务已返回结果（点击展开查看原始内容）</summary>
    <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 360, overflowY: "auto", margin: "8px 0 0" }}>{content}</pre>
  </details>;
}
