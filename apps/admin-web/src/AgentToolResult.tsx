import { useState } from "react";
import { Button, message, Space } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { api } from "./api";
import { agentOperationError } from "./AgentOperationPreview";

type DownloadResource = { name: string; endpoint: string };

const downloadableResources = (result: unknown): DownloadResource[] => {
  if (!result || typeof result !== "object") return [];
  if (Array.isArray(result)) return result.flatMap(downloadableResources);
  const item = result as Record<string, unknown>;
  if (item.type !== "resource_link") return Object.values(item).flatMap(downloadableResources);
  const isArtifact = typeof item.uri === "string" && item.uri.startsWith("oa-mcp-artifact://");
  const isSource = typeof item.uri === "string" && item.uri.startsWith("oa-mcp-source://");
  if (!isArtifact && !isSource) return [];
  const id = isArtifact ? item.artifact_id : item.resource_id;
  if (typeof id !== "string" || !/^[A-Za-z0-9_-]+$/.test(id) || typeof item.name !== "string") return [];
  if (item.uri !== `${isArtifact ? "oa-mcp-artifact" : "oa-mcp-source"}://${id}`) return [];
  const endpoint = `/agent-tools/${isArtifact ? "artifacts" : "resources"}/${id}`;
  if (item.download_url !== `${api.defaults.baseURL}${endpoint}`) return [];
  return [{ name: item.name, endpoint }];
};

export function AgentToolResult({ result, showDetails = false }: { result: unknown; showDetails?: boolean }) {
  const [downloading, setDownloading] = useState("");
  const resources = Array.from(new Map(downloadableResources(result).map((item) => [item.endpoint, item])).values());
  const download = async (resource: DownloadResource) => {
    if (downloading) return;
    setDownloading(resource.endpoint);
    try {
      const { data } = await api.get<Blob>(resource.endpoint, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = resource.name.replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_");
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error: unknown) {
      message.error(agentOperationError(error, "文件下载失败"));
    } finally {
      setDownloading("");
    }
  };
  return <>
    {!!resources.length && <Space wrap style={{ marginTop: 12 }}>
      {resources.map((resource) => <Button key={resource.endpoint} size="small" icon={<DownloadOutlined />} title={resource.name}
        loading={downloading === resource.endpoint} disabled={Boolean(downloading) && downloading !== resource.endpoint}
        style={{ height: "auto", minHeight: 24, whiteSpace: "normal", overflowWrap: "anywhere", maxWidth: "100%" }}
        onClick={() => void download(resource)}>{resource.name}</Button>)}
    </Space>}
    {showDetails && result !== undefined && result !== null && <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(result, null, 2)}</pre>}
  </>;
}
