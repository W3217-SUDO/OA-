import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, Input, message, Space, Tag } from "antd";
import { CloseOutlined, FileOutlined, InboxOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "../api";
import { clearFeedbackDraft, loadFeedbackDraft, saveFeedbackDraft } from "./draft";
import type { FeedbackPageOption } from "./navigation";
import "./feedback.css";

type Props = {
  sourceRoute: string;
  sourceControls: string[];
  openPages: FeedbackPageOption[];
  menuPages: FeedbackPageOption[];
  onCancel: () => void;
  onSubmitted?: (id: number) => void;
};

const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];
const FILE_SUFFIXES = [".png", ".jpg", ".jpeg", ".webp", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".log", ".zip", ".mp4", ".mov"];
const MAX_FILES = 10;
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

export default function FeedbackForm({ sourceRoute, sourceControls, openPages, menuPages, onCancel, onSubmitted }: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [description, setDescription] = useState("");
  const [pageKeys, setPageKeys] = useState<string[]>(sourceRoute ? [sourceRoute] : []);
  const [controls, setControls] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [draftReady, setDraftReady] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [descriptionError, setDescriptionError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const dragDepth = useRef(0);

  const labels = useMemo(() => {
    const map = new Map<string, string>();
    menuPages.forEach((page) => map.set(page.key, page.label));
    openPages.forEach((page) => { if (!map.has(page.key)) map.set(page.key, page.label); });
    return map;
  }, [menuPages, openPages]);
  // 快捷勾选：来源页排第一，其后是当前打开的页签，草稿里选过的页面也保留在这里。
  const quickPages = useMemo(() => {
    const keys = [sourceRoute, ...openPages.map((page) => page.key), ...pageKeys].filter(Boolean);
    return [...new Set(keys)].map((key) => ({ key, label: labels.get(key) || key }));
  }, [sourceRoute, openPages, pageKeys, labels]);
  // 按钮清单是点“问题反馈”那一刻从来源页读出来的，只有勾选了来源页时才出现。
  const showControls = Boolean(sourceRoute) && pageKeys.includes(sourceRoute) && sourceControls.length > 0;

  useEffect(() => {
    let cancelled = false;
    void loadFeedbackDraft().then((draft) => {
      if (cancelled) return;
      if (draft) {
        setDescription(draft.description);
        if (draft.sourceRoute === sourceRoute && draft.pageKeys.length) {
          setPageKeys(draft.pageKeys);
          setControls(draft.controls.filter((name) => sourceControls.includes(name)));
        }
        setFiles(draft.files);
        setSavedAt(draft.savedAt);
        message.info("已恢复上次未提交的反馈草稿");
      }
      setDraftReady(true);
    });
    return () => { cancelled = true; };
  }, [sourceRoute, sourceControls]);

  useEffect(() => {
    if (!draftReady || submitting) return;
    const timer = window.setTimeout(() => {
      if (!description.trim() && !files.length) { void clearFeedbackDraft(); setSavedAt(null); return; }
      void saveFeedbackDraft({ description, pageKeys, controls, sourceRoute, files }).then(setSavedAt);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [description, pageKeys, controls, sourceRoute, files, draftReady, submitting]);

  const addFiles = useCallback((incoming: File[]) => {
    const accepted: File[] = [];
    for (const file of incoming) {
      const suffix = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase() : "";
      if (!FILE_SUFFIXES.includes(suffix) && !isImage(file)) { message.warning(`不支持的文件类型：${file.name}`); continue; }
      const limit = isImage(file) ? 10 : 20;
      if (file.size > limit * 1024 * 1024) { message.warning(`${file.name} 超过 ${limit}MB`); continue; }
      accepted.push(file);
    }
    setFiles((current) => {
      const next = [...current, ...accepted];
      if (next.length > MAX_FILES) message.warning(`截图和附件合计最多 ${MAX_FILES} 个`);
      return next.slice(0, MAX_FILES);
    });
  }, []);

  // 截图后直接 Ctrl+V：剪贴板图片没有文件名，按时间补一个。
  useEffect(() => {
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
  }, [addFiles]);

  // 整个窗口都接收拖拽，避免文件落在表单外被浏览器直接打开。
  useEffect(() => {
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
  }, [addFiles]);

  const togglePage = (key: string) => setPageKeys((current) =>
    current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);

  const submit = async () => {
    const text = description.trim();
    if (text.length < 5 || text.length > 2000) { setDescriptionError("请填写 5 到 2000 字的问题描述"); return; }
    if (!pageKeys.length) { message.warning("请勾选问题所在页面"); return; }
    const body = new FormData();
    body.append("description", text);
    body.append("page", pageKeys.map((key) => labels.get(key) || key).join("、"));
    body.append("route", pageKeys[0]);
    if (showControls && controls.length) body.append("controls", controls.join("、"));
    files.forEach((file) => body.append("files", file, file.name));
    setSubmitting(true);
    try {
      const { data } = await api.post("/feedback", body);
      message.success(`反馈已提交：${data.serial_no}`);
      await clearFeedbackDraft();
      setDescription("");
      setFiles([]);
      onSubmitted?.(data.id);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "反馈提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const discardDraft = () => {
    void clearFeedbackDraft();
    setDescription("");
    setFiles([]);
    setPageKeys(sourceRoute ? [sourceRoute] : []);
    setControls([]);
    setSavedAt(null);
  };

  return <div className="feedback-form">
    {dragging && <div className="feedback-drop-mask"><InboxOutlined />松开即可添加截图或附件</div>}

    <section className="feedback-section">
      <div className="feedback-section-title"><span className="feedback-required">*</span>问题所在页面
        <span className="feedback-hint">点选即可，可多选</span></div>
      <div className="feedback-page-chips">
        {quickPages.map((page) => <Tag.CheckableTag key={page.key} checked={pageKeys.includes(page.key)}
          onChange={() => togglePage(page.key)} className="feedback-page-chip">
          {page.label}{page.key === sourceRoute && <span className="feedback-chip-badge">来源页</span>}
        </Tag.CheckableTag>)}
      </div>
    </section>

    {showControls && <section className="feedback-section">
      <div className="feedback-section-title">问题出在哪个按钮<span className="feedback-hint">来源页上的按钮，可多选；不涉及可不选</span></div>
      <div className="feedback-page-chips">
        {sourceControls.map((name) => <Tag.CheckableTag key={name} checked={controls.includes(name)}
          className="feedback-page-chip feedback-control-chip"
          onChange={() => setControls((current) => current.includes(name) ? current.filter((item) => item !== name) : [...current, name])}>
          {name}
        </Tag.CheckableTag>)}
      </div>
    </section>}

    <section className="feedback-section">
      <div className="feedback-section-title"><span className="feedback-required">*</span>问题描述</div>
      <Input.TextArea value={description} rows={7} maxLength={2000} showCount status={descriptionError ? "error" : undefined}
        aria-label="问题描述" placeholder={"请描述：\n1. 做了什么操作（点了哪个按钮、填了什么）\n2. 期望的结果\n3. 实际看到的问题"}
        onChange={(event) => { setDescription(event.target.value); if (descriptionError) setDescriptionError(""); }} />
      {descriptionError && <div className="feedback-error">{descriptionError}</div>}
    </section>

    <section className="feedback-section">
      <div className="feedback-section-title">截图和附件<span className="feedback-hint">可选，最多 {MAX_FILES} 个</span></div>
      <div className="feedback-dropzone" role="button" tabIndex={0} onClick={() => fileInput.current?.click()}
        onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") fileInput.current?.click(); }}>
        <InboxOutlined className="feedback-dropzone-icon" />
        <div>把截图或文件<b>拖到这里</b>，或截图后直接 <kbd>Ctrl</kbd>/<kbd>⌘</kbd> + <kbd>V</kbd> 粘贴</div>
        <div className="feedback-hint">也可点击选择 · 图片 PNG/JPG/WebP ≤10MB · PDF/Word/Excel/TXT/ZIP/视频 ≤20MB</div>
      </div>
      <input ref={fileInput} type="file" multiple hidden accept={FILE_SUFFIXES.join(",")}
        onChange={(event) => { addFiles(Array.from(event.target.files || [])); event.target.value = ""; }} />
      {!!files.length && <div className="feedback-files">
        {files.map((file, index) => <FilePreview key={`${file.name}-${file.size}-${index}`} file={file}
          onRemove={() => setFiles((current) => current.filter((_, i) => i !== index))} />)}
      </div>}
    </section>

    <div className="feedback-actions">
      <Space wrap>
        <Button type="primary" loading={submitting} onClick={() => void submit()}>提交反馈</Button>
        <Button onClick={onCancel} disabled={submitting}>取消</Button>
        {savedAt && <Button type="link" danger onClick={discardDraft} disabled={submitting}>清空草稿</Button>}
      </Space>
      <span className="feedback-hint">{savedAt ? `草稿已自动保存 ${dayjs(savedAt).format("HH:mm:ss")}，取消或离开后下次自动恢复` : "填写内容会自动保存为草稿"}</span>
    </div>
  </div>;
}
