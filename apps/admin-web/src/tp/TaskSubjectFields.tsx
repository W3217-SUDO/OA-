import { AutoComplete, Form, Input, message } from "antd";
import type { FormInstance } from "antd";
import type { ReactNode } from "react";
import dayjs from "dayjs";
import { api } from "../api";

// 501635（tgn 11-06）：发任务时案号和任务主题放一行；任务主题可输入，也可选常见主题，
// 选了就自动带出负责人和期限（今天起 10 天），发任务人只要写任务内容；任务内容放在主题下面，必填。
export type TaskSubjectPreset = { value: string; ownerField: "assistant_usernames" | "hearing_lawyer_usernames"; ownerLabel: string; days: number };

export const TASK_SUBJECT_PRESETS: TaskSubjectPreset[] = [
  { value: "跟进案件", ownerField: "assistant_usernames", ownerLabel: "律师助理", days: 10 },
  { value: "案件研究", ownerField: "hearing_lawyer_usernames", ownerLabel: "开庭律师", days: 10 },
];

type CasePresetPeople = { serial_no: string; assistant_usernames?: string[]; hearing_lawyer_usernames?: string[] };

async function loadCasePresetPeople(caseNo: string): Promise<CasePresetPeople | undefined> {
  const { data } = await api.get<{ items: CasePresetPeople[] }>("/tasks/case-options", { params: { keyword: caseNo, limit: 5 } });
  return data.items.find((item) => item.serial_no === caseNo);
}

/** 选了常见主题：带出负责人（本案第一位律师助理/开庭律师）和截止时间；没填案号就提示先选案件。 */
export async function applyTaskSubjectPreset(form: FormInstance, subject: string, caseNo: string) {
  const preset = TASK_SUBJECT_PRESETS.find((item) => item.value === subject);
  if (!preset) return;
  const end = dayjs().add(preset.days, "day").hour(18).minute(0).second(0);
  form.setFieldsValue({ end_at: end });
  if (!form.getFieldValue("start_at")) form.setFieldsValue({ start_at: dayjs().second(0) });
  if (!caseNo) {
    message.warning(`“${preset.value}”要带出本案${preset.ownerLabel}，请先选择关联案件`);
    return;
  }
  try {
    const owner = (await loadCasePresetPeople(caseNo))?.[preset.ownerField]?.[0];
    if (owner) form.setFieldsValue({ owner });
    else message.info(`案件 ${caseNo} 没有登记在职的${preset.ownerLabel}，请手动选择负责人`);
  } catch {
    message.info(`没能读取本案${preset.ownerLabel}，请手动选择负责人`);
  }
}

/** 第一行：案号 + 任务主题；下面一行：任务内容（必填）。 */
export function TaskSubjectFields({ form, caseField, caseNo }: { form: FormInstance; caseField: ReactNode; caseNo: () => string }) {
  return (
    <>
      <div className="form-grid task-subject-row">
        {caseField}
        <Form.Item label="任务主题" name="title" rules={[{ required: true, whitespace: true, message: "请输入或选择任务主题" }]}>
          <AutoComplete
            options={TASK_SUBJECT_PRESETS.map((item) => ({ value: item.value, label: `${item.value}（负责人：${item.ownerLabel}，期限 ${item.days} 天）` }))}
            style={{ width: "100%" }}
            placeholder="可输入，或选常见主题"
            maxLength={200}
            onSelect={(value: string) => void applyTaskSubjectPreset(form, value, caseNo())}
          />
        </Form.Item>
      </div>
      <Form.Item label="任务内容" name="description" rules={[{ required: true, whitespace: true, message: "请填写任务内容，让负责人知道要做什么" }]}>
        <Input.TextArea rows={3} placeholder="写清楚要做什么" />
      </Form.Item>
    </>
  );
}
