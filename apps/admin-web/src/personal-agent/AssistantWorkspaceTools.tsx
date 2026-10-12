import { useRef, useState } from "react";
import { Button, Segmented, Select, Tooltip, message } from "antd";
import { CloseOutlined, ExperimentOutlined, FileOutlined, FolderOpenOutlined, PaperClipOutlined } from "@ant-design/icons";
import { CaseMaterialsPicker } from "./CaseMaterialsPicker";
import { MaterialPreview } from "./MaterialPreview";
import { SkillManager } from "./SkillManager";
import { errorText, type Material, type ResponseMode } from "./types";
import { MATERIAL_ACCEPT, type usePersonalWorkspace } from "./usePersonalWorkspace";

type Props = { workspace: ReturnType<typeof usePersonalWorkspace> };

export function AssistantWorkspaceTools({ workspace }: Props) {
  const [pickerMode, setPickerMode] = useState<"case" | "materials" | null>(null);
  const [skillsOpen, setSkillsOpen] = useState(false);
  const [previewMaterial, setPreviewMaterial] = useState<Material | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  // 生成期间允许准备下一轮草稿；上传、确认、切换和停止中的真实锁仍保持禁用。
  const busy = workspace.loading || workspace.stopping || workspace.uploading || !!workspace.decisionId || workspace.conversationBusy;
  const canUseCases = workspace.status?.commands.some((item) => item.id === "cases");
  const openSkills = async () => {
    setSkillsOpen(true);
    try { await workspace.refreshSkills(); }
    catch (error) { message.error(errorText(error, "技能加载失败")); }
  };

  return <>
    <div className="assistant-context-tools">
      <Select
        className="assistant-skill-select"
        aria-label="选择技能"
        value={workspace.skillId}
        disabled={busy}
        onChange={workspace.setSkillId}
        options={workspace.skills.map((skill) => ({ value: skill.id, label: skill.name, disabled: !skill.available }))}
      />
      {workspace.status?.supports_response_modes && <Segmented
        aria-label="回答模式"
        size="small"
        value={workspace.responseMode}
        disabled={busy}
        options={[{ label: "快速", value: "fast" }, { label: "深度", value: "deep" }]}
        onChange={(value) => workspace.setResponseMode(value as ResponseMode)}
      />}
      {canUseCases && <Tooltip title={workspace.selectedCase?.title || "关联案件"}>
        <Button type="text" className="assistant-case-select" icon={<FolderOpenOutlined />} disabled={busy} onClick={() => setPickerMode("case")}>
          {workspace.selectedCase?.serial_no || "关联案件"}
        </Button>
      </Tooltip>}
      {workspace.selectedCase && <Tooltip title="选择案件材料">
        <Button type="text" icon={<FileOutlined />} disabled={busy} aria-label="选择案件材料" onClick={() => setPickerMode("materials")} />
      </Tooltip>}
      <Tooltip title="上传文件">
        <Button type="text" icon={<PaperClipOutlined />} loading={workspace.uploading} disabled={busy} aria-label="上传文件" onClick={() => fileRef.current?.click()} />
      </Tooltip>
      <Tooltip title="管理或上传技能">
        <Button type="text" icon={<ExperimentOutlined />} disabled={busy} aria-label="管理或上传技能" onClick={() => void openSkills()} />
      </Tooltip>
      <input hidden ref={fileRef} type="file" multiple accept={MATERIAL_ACCEPT} onChange={(event) => {
        void workspace.upload(Array.from(event.target.files || []));
        event.target.value = "";
      }} />
    </div>
    {(workspace.selectedCase || workspace.materials.length > 0 || workspace.caseMaterials.length > 0) && <div className="assistant-context-items">
      {workspace.selectedCase && <span className="assistant-context-item is-case">
        <FolderOpenOutlined />
        <button type="button" className="assistant-context-name" disabled={busy} title={workspace.selectedCase.title} onClick={() => setPickerMode("case")}>{workspace.selectedCase.serial_no}</button>
        <Button type="text" size="small" icon={<CloseOutlined />} disabled={busy} aria-label="取消案件关联" onClick={() => workspace.chooseCase(null)} />
      </span>}
      {[
        ...workspace.materials.map((item) => ({ ...item, source: "upload" as const })),
        ...workspace.caseMaterials.map((item) => ({ ...item, source: "case" as const })),
      ].map((item) => <span key={`${item.source}-${item.id}`} className="assistant-context-item">
        <FileOutlined />
        <button type="button" className="assistant-context-name" title={item.name} onClick={() => setPreviewMaterial(item)}>{item.name}</button>
        <Button type="text" size="small" icon={<CloseOutlined />} disabled={busy} aria-label={`移除${item.name}`} onClick={() => {
          if (item.source === "upload") workspace.setMaterials(workspace.materials.filter((value) => value.id !== item.id));
          else workspace.setCaseMaterials(workspace.caseMaterials.filter((value) => value.id !== item.id));
        }} />
      </span>)}
    </div>}
    <CaseMaterialsPicker mode={pickerMode} onClose={() => setPickerMode(null)} selectedCase={workspace.selectedCase} onCase={workspace.chooseCase} selectedMaterials={workspace.caseMaterials} onMaterials={workspace.setCaseMaterials} privateCount={workspace.materials.length} />
    <SkillManager open={skillsOpen} onClose={() => setSkillsOpen(false)} skills={workspace.skills} refresh={workspace.refreshSkills} onSelect={workspace.setSkillId} />
    <MaterialPreview item={previewMaterial} onClose={() => setPreviewMaterial(null)} />
  </>;
}
