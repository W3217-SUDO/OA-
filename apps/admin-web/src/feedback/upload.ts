import { api } from "../api";

// 截图和附件逐个上传，请求体直接是文件内容（不用 multipart 表单）：钉钉 Mac 客户端内置浏览器提交带文件的表单时
// 文字字段会丢，分开发更稳；某个文件失败只影响它自己。返回上传失败的文件名。
export async function uploadFeedbackFiles(feedbackId: number, files: File[], eventId?: number): Promise<string[]> {
  const failed: string[] = [];
  for (const file of files) {
    try {
      await api.post(`/feedback/${feedbackId}/files`, file, {
        params: { name: file.name, event_id: eventId },
        headers: { "Content-Type": file.type || "application/octet-stream" },
      });
    } catch {
      failed.push(file.name);
    }
  }
  return failed;
}

// 接口错误转成一句中文；校验错误（detail 是数组）取第一条说明。
export function feedbackErrorText(error: any, fallback: string): string {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return `${fallback}：${detail[0].msg}`;
  return fallback;
}
