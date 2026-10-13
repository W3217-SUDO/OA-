import { Alert, message, Modal } from "antd";
import { api } from "../api";
import { AgentOperationPreview } from "../AgentOperationPreview";
import { errorText } from "./types";
import { personalAiMessageSha256, type PersonalAiDocumentRequest, type PersonalAiFile, type PersonalAiSpaceInfo } from "./personalAiSpaceApi";

export async function confirmPersonalAiDocument({ conversationId, messageIndex, name, content, onSaved }: {
  conversationId: string;
  messageIndex: number;
  name: string;
  content: string;
  onSaved: (file: PersonalAiFile) => void;
}): Promise<void> {
  const { data: space } = await api.get<PersonalAiSpaceInfo>("/personal-agent/ai-space");
  if (!space.configured) throw new Error("个人 AI 空间 OSS 尚未配置，不能保存文件");
  const body: PersonalAiDocumentRequest = { conversation_id: conversationId, message_index: messageIndex, name, expected_content_sha256: await personalAiMessageSha256(content) };
  const path = "/personal-agent/ai-space/files";
  return new Promise((resolve) => {
    let submitted = false;
    let saving = false;
    const preview = (error?: string) => <div className="personal-ai-document-preview">
      {error && <Alert type="error" showIcon title="文档保存未完成" description={error} />}
      <AgentOperationPreview action={{ id: `personal-document-${conversationId}-${messageIndex}`, type: "personal.document.create", summary: `保存 ${name} 到${space.owner_name}的个人 AI 空间`, preview: { operation_name: "保存个人 AI 空间 Word 文档", target: space.owner_name, method: "POST", path, params: { body } } }} />
      <pre>{content}</pre>
    </div>;
    const modal = Modal.confirm({
      title: "保存个人 AI 空间 Word 文档", width: 760, className: "personal-ai-document-confirmation",
      okText: "确认保存", cancelText: "暂不保存", content: preview(),
      onCancel: () => { if (!saving) resolve(); },
      onOk: async () => {
        if (submitted) throw new Error("已提交保存请求，请在个人 AI 空间核对结果，禁止重复提交");
        submitted = true;
        saving = true;
        modal.update({ cancelButtonProps: { disabled: true }, closable: false, keyboard: false, maskClosable: false });
        try {
          const { data: file } = await api.post<PersonalAiFile>("/personal-agent/ai-space/files", body, { headers: { "X-OA-Agent-Confirmation": "frontend" } });
          if (file.status !== "available") throw new Error(file.error || `文件保存状态：${file.status}，请在个人 AI 空间核对`);
          if (file.owner_user_id !== space.owner_user_id || file.conversation_id !== conversationId) throw new Error("保存返回的归属或来源会话不匹配，请在个人 AI 空间核对，禁止重复提交");
          onSaved(file);
          message.success(`Word 文档已保存到个人 AI 空间：${file.name}`);
          resolve();
        } catch (error) {
          const text = errorText(error, "文档保存失败，请在个人 AI 空间核对结果");
          modal.update({ content: preview(text), okButtonProps: { disabled: true }, cancelButtonProps: { disabled: false } });
          throw error;
        } finally { saving = false; }
      },
    });
  });
}
