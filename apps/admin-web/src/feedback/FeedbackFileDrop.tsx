import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";
import { message } from "antd";
import { CloseOutlined, FileOutlined, InboxOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import "./feedback.css";

const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];
export const FEEDBACK_FILE_SUFFIXES = [".png", ".jpg", ".jpeg", ".webp", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".log", ".zip", ".mp4", ".mov"];
export const FEEDBACK_MAX_FILES = 10;
const isImage = (file: File) => IMAGE_TYPES.includes(file.type);
const formatSize = (size: number) => size >= 1024 * 1024 ? `${(size / 1024 / 1024).toFixed(1)}MB` : `${Math.max(1, Math.round(size / 1024))}KB`;

function FilePreview({ file, onRemove }: { file: File; onRemove: () => void }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    if (!isImage(file)) return;
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  return <div className="feedback-file" title={file.name}>
    {url ? <img src={url} alt={file.name} /> : <div className="feedback-file-icon"><FileOutlined /></div>}
    <div className="feedback-file-name">{file.name}</div>
    <div className="feedback-file-size">{formatSize(file.size)}</div>
    <button type="button" className="feedback-file-remove" aria-label={`移除 ${file.name}`} onClick={onRemove}><CloseOutlined /></button>
  </div>;
}

type Props = {
  files: File[];
  onChange: (files: File[]) => void;
  /** 反馈详情里回复用的小号上传区。 */
  compact?: boolean;
  disabled?: boolean;
  /** 聊天框输入行用：不显示上传区，由外面的“＋”按钮通过 pickerRef 打开文件选择；粘贴、拖拽照常可用。 */
  inline?: boolean;
  pickerRef?: MutableRefObject<(() => void) | null>;
};

// 截图和附件上传区：拖到窗口任意位置、截图后 Ctrl/⌘+V 粘贴或点击选择都可以；提交反馈和详情回复共用。
export default function FeedbackFileDrop({ files, onChange, compact = false, disabled = false, inline = false, pickerRef }: Props) {
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  if (pickerRef) pickerRef.current = () => fileInput.current?.click();
  const dragDepth = useRef(0);
  const filesRef = useRef(files);
  filesRef.current = files;

  const addFiles = useCallback((incoming: File[]) => {
    const accepted: File[] = [];
    for (const file of incoming) {
      const suffix = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase() : "";
      if (!FEEDBACK_FILE_SUFFIXES.includes(suffix) && !isImage(file)) { message.warning(`不支持的文件类型：${file.name}`); continue; }
      const limit = isImage(file) ? 10 : 20;
      if (file.size > limit * 1024 * 1024) { message.warning(`${file.name} 超过 ${limit}MB`); continue; }
      accepted.push(file);
    }
    const next = [...filesRef.current, ...accepted];
    if (next.length > FEEDBACK_MAX_FILES) message.warning(`截图和附件合计最多 ${FEEDBACK_MAX_FILES} 个`);
    // 连续粘贴、拖入时页面还没重新渲染，先更新这里，避免后一次覆盖前一次。
    filesRef.current = next.slice(0, FEEDBACK_MAX_FILES);
    onChange(filesRef.current);
  }, [onChange]);

  // 截图后直接 Ctrl+V：剪贴板图片没有文件名，按时间补一个。
  useEffect(() => {
    if (disabled) return;
    const onPaste = (event: ClipboardEvent) => {
      const pasted = Array.from(event.clipboardData?.files || []);
      if (!pasted.length) return;
      event.preventDefault();
      addFiles(pasted.map((file, index) => file.name && file.name !== "image.png" ? file : new File(
        [file], `截图-${dayjs().format("YYYYMMDD-HHmmss")}${index ? `-${index}` : ""}.${file.type.split("/")[1] === "jpeg" ? "jpg" : file.type.split("/")[1] || "png"}`,
        { type: file.type },
      )));
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [addFiles, disabled]);

  // 整个窗口都接收拖拽，避免文件落在上传区外被浏览器直接打开。
  useEffect(() => {
    if (disabled) return;
    const hasFiles = (event: DragEvent) => Array.from(event.dataTransfer?.types || []).includes("Files");
    const onEnter = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      dragDepth.current += 1;
      setDragging(true);
    };
    const onOver = (event: DragEvent) => { if (hasFiles(event)) event.preventDefault(); };
    const onLeave = () => {
      dragDepth.current = Math.max(0, dragDepth.current - 1);
      if (!dragDepth.current) setDragging(false);
    };
    const onDrop = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      dragDepth.current = 0;
      setDragging(false);
      addFiles(Array.from(event.dataTransfer?.files || []));
    };
    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragover", onOver);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragover", onOver);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("drop", onDrop);
    };
  }, [addFiles, disabled]);

  return <>
    {dragging && <div className="feedback-drop-mask"><InboxOutlined />松开即可添加截图或附件</div>}
    {!inline && <div className={`feedback-dropzone${compact ? " is-compact" : ""}`} role="button" tabIndex={0} aria-label="添加截图或附件"
      onClick={() => fileInput.current?.click()}
      onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") fileInput.current?.click(); }}>
      <InboxOutlined className="feedback-dropzone-icon" />
      <div>把截图或文件<b>拖到这里</b>，或截图后直接 <kbd>Ctrl</kbd>/<kbd>⌘</kbd> + <kbd>V</kbd> 粘贴{compact ? "，也可点击选择" : ""}</div>
      {!compact && <div className="feedback-hint">也可点击选择 · 图片 PNG/JPG/WebP ≤10MB · PDF/Word/Excel/TXT/ZIP/视频 ≤20MB</div>}
    </div>}
    <input ref={fileInput} type="file" multiple hidden accept={FEEDBACK_FILE_SUFFIXES.join(",")}
      onChange={(event) => { addFiles(Array.from(event.target.files || [])); event.target.value = ""; }} />
    {!!files.length && <div className={`feedback-files${inline ? " is-inline" : ""}`}>
      {files.map((file, index) => <FilePreview key={`${file.name}-${file.size}-${index}`} file={file}
        onRemove={() => onChange(files.filter((_, i) => i !== index))} />)}
    </div>}
  </>;
}
