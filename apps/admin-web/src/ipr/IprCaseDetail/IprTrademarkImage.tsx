import { useEffect, useState } from "react";
import { Button, Upload, message } from "antd";
import { api } from "../../api";
import { roleActionAllowed } from "../../roleActions";
import type { IprRecord } from "../types";

/** 商标案件页右上角的商标图样（原系统同位置；没上传时显示默认 ®），可上传或更换（BUG20261030005）。 */
export function IprTrademarkImage({ detail, onSaved }: { detail: IprRecord; onSaved?: (attachmentId: number) => void }) {
  const imageId = detail.data.trademark_image_attachment_id;
  const [url, setUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  useEffect(() => {
    if (!imageId) { setUrl(""); return undefined; }
    let objectUrl = "";
    let alive = true;
    api.get<Blob>(`/ipr/cases/${detail.id}/trademark-image`, { responseType: "blob" })
      .then(({ data }) => { if (alive) { objectUrl = URL.createObjectURL(data); setUrl(objectUrl); } })
      .catch(() => alive && setUrl(""));
    return () => { alive = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [detail.id, imageId]);
  const upload = async (file: File) => {
    const payload = new FormData();
    payload.append("file", file);
    setUploading(true);
    try {
      const { data } = await api.put<{ attachment_id: number }>(`/ipr/cases/${detail.id}/trademark-image`, payload);
      message.success("商标图样已上传");
      onSaved?.(data.attachment_id);
    } catch (failure: any) {
      message.error(failure?.response?.data?.detail || "商标图样上传失败");
    } finally {
      setUploading(false);
    }
  };
  const canUpload = detail.status !== "已结案" && roleActionAllowed("ipr.case.update");
  return (
    <div className="ipr-trademark-image">
      <div className="ipr-trademark-image-frame">
        {url ? <img src={url} alt="商标图样" /> : <span className="ipr-trademark-image-default" aria-label="未上传商标图样">®</span>}
      </div>
      {canUpload ? (
        <Upload accept=".png,.jpg,.jpeg,.gif,.bmp" showUploadList={false} beforeUpload={(file) => { void upload(file); return false; }}>
          <Button size="small" loading={uploading}>{imageId ? "更换图样" : "上传图样"}</Button>
        </Upload>
      ) : null}
    </div>
  );
}
