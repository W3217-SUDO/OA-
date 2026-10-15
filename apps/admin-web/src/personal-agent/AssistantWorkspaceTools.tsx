import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Button, Popover, Segmented, Select, Tooltip, message } from "antd";
import { CloseOutlined, ExperimentOutlined, FileOutlined, FolderOpenOutlined, PaperClipOutlined, PlusOutlined, SettingOutlined } from "@ant-design/icons";
import { CaseMaterialsPicker } from "./CaseMaterialsPicker";
import { MaterialPreview } from "./MaterialPreview";
import { SkillManager } from "./SkillManager";
import { skillChoiceLabel } from "./skillScope";
import { errorText, type Material, type ResponseMode } from "./types";
import { MATERIAL_ACCEPT, type usePersonalWorkspace } from "./usePersonalWorkspace";
import "./assistant-workspace-tools.css";

export type AssistantWorkspaceToolsHandle = { importSkills: () => void };
type Props = { workspace: ReturnType<typeof usePersonalWorkspace>; onOpenPersonalAiSpace: () => void; onOpenMemory?: () => void; desktopWorkspace?: boolean };

export const AssistantWorkspaceTools = forwardRef<AssistantWorkspaceToolsHandle, Props>(function AssistantWorkspaceTools({ workspace, onOpenPersonalAiSpace, onOpenMemory, desktopWorkspace = false }, ref) {
  const [mobile, setMobile] = useState(() => window.matchMedia("(max-width: 991px)").matches);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [pickerMode, setPickerMode] = useState<"case" | "materials" | null>(null);
  const [skillsOpen, setSkillsOpen] = useState(false);
  const [previewMaterial, setPreviewMaterial] = useState<Material | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  // 生成期间允许准备下一轮草稿；上传、确认、切换和停止中的真实锁仍保持禁用。
  const busy = workspace.loading || workspace.stopping || workspace.uploading || !!workspace.decisionId || workspace.conversationBusy;
  const canUseCases = workspace.status?.commands.some((item) => item.id === "cases");
  useEffect(() => {
    const media = window.matchMedia("(max-width: 991px)");
    const update = () => { setMobile(media.matches); setToolsOpen(false); };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  const openPicker = (mode: "case" | "materials") => {
    if (busy || workspace.loadError || !canUseCases) return;
    setToolsOpen(false); setPickerMode(mode);
  };
  const openSkills = async () => {
    if (busy) return;
    setToolsOpen(false);
    setSkillsOpen(true);
    try { await workspace.refreshSkills(); }
    catch (error) { message.error(errorText(error, "技能加载失败")); }
  };
  useImperativeHandle(ref, () => ({ importSkills: () => void openSkills() }));

  const controls = <div className="assistant-context-controls" role={mobile ? "dialog" : undefined} aria-label="对话工具" onKeyDown={(event) => {
    if (mobile && event.key === "Escape") { event.stopPropagation(); setToolsOpen(false); triggerRef.current?.focus(); }
  }}>
      <Select
        className="assistant-skill-select"
        aria-label="选择技能"
        value={workspace.skillId}
        disabled={busy}
        onChange={workspace.setSkillId}
        options={workspace.skills.map((skill) => ({ value: skill.id, label: skillChoiceLabel(skill), disabled: !skill.available }))}
      />
      {workspace.status?.supports_response_modes && <Segmented
        aria-label="回答模式"
        size="small"
        value={workspace.responseMode}
        disabled={busy}
        options={[{ label: "快速", value: "fast" }, { label: "深度", value: "deep" }]}
        onChange={(value) => workspace.setResponseMode(value as ResponseMode)}
      />}
      {canUseCases && <Tooltip title={desktopWorkspace ? "选择案件及具体文件" : workspace.selectedCase?.title || "关联案件"}>
        <Button type="text" htmlType="button" className="assistant-case-select" icon={<FolderOpenOutlined />} disabled={busy || !!workspace.loadError} onClick={() => openPicker(desktopWorkspace && workspace.selectedCase ? "materials" : "case")}>
          {desktopWorkspace ? `案件文件${workspace.caseMaterials.length ? `（${workspace.caseMaterials.length}）` : ""}` : workspace.selectedCase?.serial_no || "关联案件"}
        </Button>
      </Tooltip>}
      {!desktopWorkspace && workspace.selectedCase && <Tooltip title="选择案件材料">
        <Button type="text" htmlType="button" icon={<FileOutlined />} disabled={busy || !!workspace.loadError} aria-label="选择案件材料" onClick={() => openPicker("materials")} />
      </Tooltip>}
      <Tooltip title="上传文件">
        <Button type="text" htmlType="button" icon={<PaperClipOutlined />} loading={workspace.uploading} disabled={busy} aria-label="上传文件" onClick={() => { setToolsOpen(false); fileRef.current?.click(); }} />
      </Tooltip>
      {!desktopWorkspace && <Tooltip title="导入技能">
        <Button type="text" htmlType="button" className="assistant-skills-manage" icon={<ExperimentOutlined />} disabled={busy} aria-label="导入技能" onClick={() => void openSkills()}>技能</Button>
      </Tooltip>}
      {onOpenMemory && <Button type="text" htmlType="button" icon={<SettingOutlined />} aria-label="记忆管理" onClick={() => { setToolsOpen(false); onOpenMemory(); }}>记忆管理</Button>}
      {mobile && <Button type="text" htmlType="button" className="personal-ai-space-mobile-entry" icon={<FolderOpenOutlined />} onClick={() => { setToolsOpen(false); onOpenPersonalAiSpace(); }}>个人 AI 空间</Button>}
    </div>;

  return <>
    <div className="assistant-context-tools">
      {mobile ? <Popover
        placement="topLeft"
        trigger="click"
        open={toolsOpen}
        onOpenChange={setToolsOpen}
        getPopupContainer={() => document.body}
        classNames={{ root: "assistant-tools-popover" }}
        content={controls}
      >
        <Tooltip title="对话工具">
          <Button ref={triggerRef} type="text" htmlType="button" className="assistant-tools-trigger" icon={<PlusOutlined />} disabled={busy} aria-label="对话工具" aria-haspopup="dialog" aria-expanded={toolsOpen} onKeyDown={(event) => {
            if (event.key === "Escape") setToolsOpen(false);
          }} />
        </Tooltip>
      </Popover> : controls}
      <input hidden ref={fileRef} type="file" multiple accept={MATERIAL_ACCEPT} onChange={(event) => {
        void workspace.upload(Array.from(event.target.files || []));
        event.target.value = "";
      }} />
    </div>
    {(workspace.selectedCase || workspace.materials.length > 0 || workspace.caseMaterials.length > 0) && <div className="assistant-context-items">
      {workspace.selectedCase && (!desktopWorkspace || workspace.caseMaterials.length > 0) && <span className="assistant-context-item is-case">
        <FolderOpenOutlined />
        <button type="button" className="assistant-context-name" disabled={busy} title={workspace.selectedCase.title} onClick={() => openPicker("case")}>{workspace.selectedCase.serial_no}</button>
        <Tooltip title="取消案件关联"><Button type="text" htmlType="button" size="small" icon={<CloseOutlined />} disabled={busy} aria-label="取消案件关联" onClick={() => workspace.chooseCase(null)} /></Tooltip>
      </span>}
      {[
        ...workspace.materials.map((item) => ({ ...item, source: "upload" as const })),
        ...workspace.caseMaterials.map((item) => ({ ...item, source: "case" as const })),
      ].map((item) => <span key={`${item.source}-${item.id}`} className="assistant-context-item">
        <FileOutlined />
        <button type="button" className="assistant-context-name" title={item.name} onClick={() => setPreviewMaterial(item)}>{item.name}</button>
        <Tooltip title={`移除${item.name}`}><Button type="text" htmlType="button" size="small" icon={<CloseOutlined />} disabled={busy} aria-label={`移除${item.name}`} onClick={() => {
          if (item.source === "upload") workspace.setMaterials(workspace.materials.filter((value) => value.id !== item.id));
          else {
            const remaining = workspace.caseMaterials.filter((value) => value.id !== item.id);
            if (desktopWorkspace && !remaining.length) workspace.chooseCase(null);
            else workspace.setCaseMaterials(remaining);
          }
        }} /></Tooltip>
      </span>)}
    </div>}
    <CaseMaterialsPicker mode={pickerMode} onClose={() => setPickerMode(null)} selectedCase={workspace.selectedCase} onCase={workspace.chooseCase} selectedMaterials={workspace.caseMaterials} onMaterials={workspace.setCaseMaterials} privateCount={workspace.materials.length} onSelection={desktopWorkspace ? workspace.chooseCaseMaterials : undefined} />
    <SkillManager open={skillsOpen} onClose={() => setSkillsOpen(false)} skills={workspace.skills} refresh={workspace.refreshSkills} onSelect={workspace.setSkillId} mode="import-only" scope="personal" />
    <MaterialPreview item={previewMaterial} onClose={() => setPreviewMaterial(null)} />
  </>;
});
