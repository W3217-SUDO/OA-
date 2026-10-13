import { useState } from "react";
import { Button, Drawer, Select, Tooltip } from "antd";
import { AppstoreAddOutlined, FolderOpenOutlined, PaperClipOutlined, PlusOutlined } from "@ant-design/icons";
import type { WorkspaceCase, WorkspaceSkill } from "./types";
import { skillChoiceLabel } from "./skillScope";

type Props = {
  skills: WorkspaceSkill[];
  skillId: string;
  busy: boolean;
  uploading: boolean;
  canUseCases: boolean;
  selectedCase: WorkspaceCase | null;
  onSkill: (id: string) => void;
  onCase: () => void;
  onMaterials: () => void;
  onUpload: () => void;
  onSkills: () => void;
};

export function MobileComposerOptions({ skills, skillId, busy, uploading, canUseCases, selectedCase, onSkill, onCase, onMaterials, onUpload, onSkills }: Props) {
  const [open, setOpen] = useState(false);
  const selectedSkill = skills.find((item) => item.id === skillId);

  return <>
    <div className="workspace-mobile-composer-options">
      <Tooltip title={selectedSkill ? `对话工具 · ${selectedSkill.name}` : "对话工具"}>
        <Button type="text" icon={<PlusOutlined />} aria-label={selectedSkill ? `打开对话工具，当前技能：${selectedSkill.name}` : "打开对话工具"} aria-haspopup="dialog" aria-expanded={open} loading={uploading} disabled={busy} onClick={() => setOpen(true)}>
          {selectedSkill && <span className="workspace-mobile-skill-name">{skillChoiceLabel(selectedSkill)}</span>}
        </Button>
      </Tooltip>
    </div>
    <Drawer title="对话工具" placement="bottom" height="auto" rootClassName="workspace-mobile-composer-drawer" open={open} onClose={() => setOpen(false)}>
      <div className="workspace-mobile-composer-sheet">
        <label className="workspace-mobile-skill-field">
          <span>办公技能</span>
          <Select aria-label="选择办公技能" value={skillId} disabled={busy} onChange={onSkill} popupMatchSelectWidth options={skills.map((item) => ({ value: item.id, label: skillChoiceLabel(item), disabled: !item.available, title: item.description }))} />
        </label>
        {canUseCases && <Button icon={<FolderOpenOutlined />} disabled={busy} title={selectedCase?.title} onClick={() => { setOpen(false); onCase(); }}>{selectedCase ? `关联案件 · ${selectedCase.serial_no}` : "关联案件"}</Button>}
        {selectedCase && <Button icon={<FolderOpenOutlined />} disabled={busy} onClick={() => { setOpen(false); onMaterials(); }}>选择案件材料</Button>}
        <Button icon={<PaperClipOutlined />} loading={uploading} disabled={busy} onClick={() => { setOpen(false); onUpload(); }}>上传文件</Button>
        <Button icon={<AppstoreAddOutlined />} disabled={busy} onClick={() => { setOpen(false); onSkills(); }}>管理技能</Button>
      </div>
    </Drawer>
  </>;
}
