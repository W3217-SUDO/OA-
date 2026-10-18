import { message, Modal } from "antd";
import { api } from "../../api";
import { AgentOperationPreview, agentOperationError } from "../../AgentOperationPreview";

export function confirmCaseAgentDocument({ caseId, serialNo, name, content, onSaved }: {
  caseId: number;
  serialNo: string;
  name: string;
  content: string;
  onSaved: () => Promise<void>;
}) {
  const path = `/cases/${caseId}/ai-space/files`;
  Modal.confirm({
    title: "保存案件智能体文件夹 Word 文档",
    width: 760,
    okText: "确认保存",
    cancelText: "暂不保存",
    content: <div style={{ maxHeight: "60dvh", overflowY: "auto" }}><AgentOperationPreview action={{
      id: `document-${caseId}`, type: "case.document.create", summary: `保存 ${name} 到案件智能体文件夹`,
      preview: { operation_name: "保存案件智能体文件夹 Word 文档", target: serialNo, method: "POST", path, params: { body: { name, content } } },
    }} /></div>,
    onOk: async () => {
      try {
        await api.post(path, { name, content }, { headers: { "X-OA-Agent-Confirmation": "frontend" } });
      } catch (error: unknown) {
        message.error(agentOperationError(error, "文档保存失败"));
        throw error;
      }
      message.success(`Word 文档已保存到案件智能体文件夹：${name}`);
      try {
        await onSaved();
      } catch (error: unknown) {
        message.error(`文档已保存，但列表刷新失败：${agentOperationError(error, "请刷新案件材料")}`);
      }
    },
  });
}
