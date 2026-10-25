import { useEffect, useMemo, useState } from "react";
import { Button, Input, message, Space, Tag } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import FeedbackFileDrop, { FEEDBACK_MAX_FILES } from "./FeedbackFileDrop";
import { feedbackErrorText, uploadFeedbackFiles } from "./upload";
import { clearFeedbackDraft, loadFeedbackDraft, saveFeedbackDraft } from "./draft";
import type { FeedbackPageOption } from "./navigation";
import "./feedback.css";

type Props = {
  sourceRoute: string;
  pageControls: Record<string, string[]>;
  openPages: FeedbackPageOption[];
  menuPages: FeedbackPageOption[];
  onCancel: () => void;
  onSubmitted?: (id: number) => void;
};

const MAX_FILES = FEEDBACK_MAX_FILES;

export default function FeedbackForm({ sourceRoute, pageControls, openPages, menuPages, onCancel, onSubmitted }: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [description, setDescription] = useState("");
  const [pageKeys, setPageKeys] = useState<string[]>(sourceRoute ? [sourceRoute] : []);
  const [controls, setControls] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [draftReady, setDraftReady] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [descriptionError, setDescriptionError] = useState("");

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
  // 勾选了哪些页面就列出哪些页面的按钮；按钮清单是本次登录后打开过该页面时读出来的。
  // 选中的按钮记成“页面::按钮名”，同名按钮在不同页面互不影响。
  const controlKey = (route: string, name: string) => `${route}::${name}`;
  const controlGroups = pageKeys.map((key) => ({
    key, label: labels.get(key) || key, names: pageControls[key] || [],
  }));
  const showControls = controlGroups.length > 0;
  const toggleControl = (key: string) => setControls((current) =>
    current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);

  useEffect(() => {
    let cancelled = false;
    void loadFeedbackDraft().then((draft) => {
      if (cancelled) return;
      if (draft) {
        setDescription(draft.description);
        if (draft.sourceRoute === sourceRoute && draft.pageKeys.length) {
          setPageKeys(draft.pageKeys);
          setControls(draft.controls.filter((key) => {
            const [route, ...rest] = key.split("::");
            return (pageControls[route] || []).includes(rest.join("::"));
          }));
        }
        setFiles(draft.files);
        setSavedAt(draft.savedAt);
        message.info("已恢复上次未提交的反馈草稿");
      }
      setDraftReady(true);
    });
    return () => { cancelled = true; };
  }, [sourceRoute, pageControls]);

  useEffect(() => {
    if (!draftReady || submitting) return;
    const timer = window.setTimeout(() => {
      if (!description.trim() && !files.length) { void clearFeedbackDraft(); setSavedAt(null); return; }
      void saveFeedbackDraft({ description, pageKeys, controls, sourceRoute, files }).then(setSavedAt);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [description, pageKeys, controls, sourceRoute, files, draftReady, submitting]);


  const togglePage = (key: string) => setPageKeys((current) =>
    current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);

  const submit = async () => {
    const text = description.trim();
    if (!text) { setDescriptionError("请填写问题描述"); return; }
    if (!pageKeys.length) { message.warning("请勾选问题所在页面"); return; }
    // 只勾了一个页面时只写按钮名；多个页面时带上页面名，处理人分得清是哪个页面的按钮。
    const chosen = controlGroups.flatMap((group) => group.names
      .filter((name) => controls.includes(controlKey(group.key, name)))
      .map((name) => pageKeys.length > 1 ? `${group.label}·${name}` : name));
    setSubmitting(true);
    try {
      // 先用 JSON 建好反馈，再逐个上传截图和附件（见 upload.ts）。
      const { data } = await api.post("/feedback/submit", {
        description: text, page: pageKeys.map((key) => labels.get(key) || key).join("、"),
        route: pageKeys[0], controls: chosen,
      });
      const failed = await uploadFeedbackFiles(data.id, files);
      if (failed.length) message.warning(`反馈已提交：${data.serial_no}，但 ${failed.join("、")} 没有传上去，请在详情里回复补传`, 6);
      else message.success(`反馈已提交：${data.serial_no}`);
      await clearFeedbackDraft();
      setDescription("");
      setFiles([]);
      onSubmitted?.(data.id);
    } catch (error: any) {
      message.error(feedbackErrorText(error, "反馈提交失败"));
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
      <div className="feedback-section-title">问题出在哪个按钮<span className="feedback-hint">勾选页面上的按钮，可多选；不涉及可不选</span></div>
      {controlGroups.map((group) => <div key={group.key} className="feedback-control-group">
        {controlGroups.length > 1 && <div className="feedback-control-group-title">{group.label}</div>}
        {group.names.length ? <div className="feedback-page-chips">
          {group.names.map((name) => <Tag.CheckableTag key={name} checked={controls.includes(controlKey(group.key, name))}
            className="feedback-page-chip feedback-control-chip" onChange={() => toggleControl(controlKey(group.key, name))}>
            {name}
          </Tag.CheckableTag>)}
        </div> : <div className="feedback-hint feedback-control-empty">本次登录后还没打开过这个页面，先打开一次再回来就能选按钮</div>}
      </div>)}
    </section>}

    <section className="feedback-section">
      <div className="feedback-section-title"><span className="feedback-required">*</span>问题描述</div>
      <Input.TextArea value={description} rows={7} status={descriptionError ? "error" : undefined}
        aria-label="问题描述" placeholder={"请描述：\n1. 做了什么操作（点了哪个按钮、填了什么）\n2. 期望的结果\n3. 实际看到的问题"}
        onChange={(event) => { setDescription(event.target.value); if (descriptionError) setDescriptionError(""); }} />
      {descriptionError && <div className="feedback-error">{descriptionError}</div>}
    </section>

    <section className="feedback-section">
      <div className="feedback-section-title">截图和附件<span className="feedback-hint">可选，最多 {MAX_FILES} 个</span></div>
      <FeedbackFileDrop files={files} onChange={setFiles} disabled={submitting} />
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
