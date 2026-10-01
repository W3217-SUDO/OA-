import { message } from "antd";
import type { FormInstance } from "antd";
import type { Dispatch, Key, SetStateAction } from "react";
import { api } from "../../api";
import { buildCasePhaseChangePayload } from "../../caseSecondBatchParity";
import { ARCHIVE_LOCKED_STATUSES } from "../constants";
import type { CasePhaseOption, CaseRow } from "../types";

export interface CasePhaseChangeFormValues {
  case_phase_id?: number;
  comment?: string;
}

export interface CasePhaseActionsDependencies {
  phaseForm: FormInstance<CasePhaseChangeFormValues>;
  phaseEditing: CaseRow[] | null;
  phaseOptions: CasePhaseOption[];
  setPhaseEditing: Dispatch<SetStateAction<CaseRow[] | null>>;
  setPhaseOptions: Dispatch<SetStateAction<CasePhaseOption[]>>;
  setSelectedCaseKeys: Dispatch<SetStateAction<Key[]>>;
  isCaseDetailView: boolean;
  viewingCounselCase: CaseRow | null;
  openCounselDetail: (row: CaseRow) => Promise<void>;
  load: () => Promise<void>;
}

export function createCasePhaseActions(context: CasePhaseActionsDependencies) {
    const openPhaseChange = async (rows: CaseRow[]) => {
        const { setPhaseOptions, phaseForm, setPhaseEditing } = context;
        const selected = rows.filter(Boolean);
        if (!selected.length)
            return message.warning("请先选择案件");
        const selectedCaseTypes = Array.from(new Set(selected.map((row) => String(row.data.case_type || "").trim())));
        if (selectedCaseTypes.length > 1)
            return message.warning("不同案件类型的阶段范围不同，请分别修改");
        if (selected.some((row) => [...ARCHIVE_LOCKED_STATUSES, "已合并"].includes(row.status)))
            return message.warning("归档中、已归档或已合并案件不能修改案件阶段");
        try {
            const { data } = await api.get("/cases/phases", { params: { case_type: selectedCaseTypes[0] || "" } });
            // 接口已按案件类型筛选阶段；此处再次筛选会误删历史类型别名对应的有效阶段。
            const options = (Array.isArray(data?.items) ? data.items : []) as CasePhaseOption[];
            if (!options.length)
                return message.error("案件阶段加载失败");
            setPhaseOptions(options);
            const current = selected[0];
            const currentOption = options.find((option) => Number(current.data.case_phase_id) === option.id || option.canonical_name === current.status || option.name === current.status);
            phaseForm.resetFields();
            phaseForm.setFieldsValue({ case_phase_id: currentOption?.id || options[0].id, comment: "" });
            setPhaseEditing(selected);
        }
        catch (error: any) {
            message.error(error?.response?.data?.detail || "案件阶段加载失败");
        }
    };
    const savePhaseChange = async () => {
        const { phaseEditing, phaseForm, phaseOptions, setPhaseEditing, setSelectedCaseKeys, isCaseDetailView, viewingCounselCase, openCounselDetail, load } = context;
        if (!phaseEditing?.length)
            return;
        const values = await phaseForm.validateFields();
        const option = phaseOptions.find((item) => item.id === Number(values.case_phase_id));
        if (!option)
            return message.error("案件阶段不存在或已停用");
        try {
            const changedCases = phaseEditing;
            const { data } = await api.post("/cases/phase-change", buildCasePhaseChangePayload(changedCases.map((row) => row.serial_no), option.id, option.name, values.comment));
            message.success("修改成功！");
            setPhaseEditing(null);
            phaseForm.resetFields();
            setSelectedCaseKeys([]);
            const currentDetailChanged = isCaseDetailView && viewingCounselCase
                && changedCases.some((row) => row.id === viewingCounselCase.id);
            if (currentDetailChanged) {
                const updatedDetail = (Array.isArray(data?.items) ? data.items : [])
                    .find((row: CaseRow) => row.id === viewingCounselCase.id) || viewingCounselCase;
                await openCounselDetail(updatedDetail);
            }
            await load();
        }
        catch (error: unknown) {
            const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            message.error(detail || "修改失败！");
        }
    };
    return { openPhaseChange, savePhaseChange };
}
