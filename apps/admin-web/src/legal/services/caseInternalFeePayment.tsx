import { Button, message, Modal } from "antd";
import { api } from "../../api";
import { rememberInternalApplicationQuery } from "../../finance/internalApplicationNavigation";
import type { CaseRow } from "../types";
import type { CaseFinanceDependencies } from "./financeActions";

const waitingReasons: Record<string, string> = {
  待到账: "费用尚处于待到账环节，请查看现有请款单的处理进度。",
  待分配: "来源回款尚未完成分配。",
  待结算: "来源费用尚未完成结算。",
  待归档: "案件尚未完成归档。",
  待审批: "请款单已进入审批，请勿重复申请。",
};

const internalFee = (row: CaseRow) => row.data.expense_scope === "内部" || String(row.data.fee_type || "").includes("内部");

function amount(value: unknown, name: string, optional = false): number {
  if ((value == null || value === "") && optional) return 0;
  if (value == null || value === "" || !Number.isFinite(Number(value))) throw new Error(`${name}不可读取，请核对金额权限及费用资料`);
  return Number(value);
}

/** 沿案件详情原有读取权限刷新完整选择，已申请只读定位，不进入出纳付款包。 */
export async function prepareInternalFeePayment(
  selected: CaseRow[], caseRecord: CaseRow, username: string, onNavigate?: (route: string) => void,
): Promise<CaseRow[] | null> {
  const ids = new Set(selected.map((row) => row.id));
  if (!ids.size) throw new Error("请先选择需要申请付款的内部费用");
  const response = await api.get(`/cases/${caseRecord.id}/relations`, { params: { include: "fees" } });
  if (!Array.isArray(response.data?.fees)) throw new Error("案件费用读取结果无效，请刷新后重试");
  const rows = (response.data.fees as CaseRow[]).filter((row) => ids.has(row.id));
  if (rows.length !== ids.size || rows.some((row) => !internalFee(row))) throw new Error("部分费用已变化或无权查看，请刷新后重新选择");
  if (rows.some((row) => {
    const caseNo = String(row.data.case_no || "").trim();
    const linkedIds = [row.data.case_id, row.data.case_record_id].filter((value) => value != null && value !== "" && Number(value) !== 0);
    // 原关系接口已按案件授权过滤；缺少历史案号不是跨案，有明确冲突才阻止。
    return (caseNo && caseNo !== caseRecord.serial_no) || linkedIds.some((value) => Number(value) !== caseRecord.id);
  })) {
    throw new Error("所选费用不属于当前案件，不能一起申请付款");
  }
  const applications = rows.filter((row) => String(row.data.payment_application_no || "").trim()
    || String(row.data.applicant || "").trim() || row.data.internal_application_id);
  if (applications.length) {
    const groups = Array.from(new Map(applications.map((row) => [
      String(row.data.payment_application_no || row.data.internal_application_id || row.serial_no), row,
    ])).values());
    const notice = Modal.info({
      title: "所选费用已有请款申请",
      className: "case-internal-payment-notice",
      width: 540,
      okText: "关闭",
      content: <div className="case-internal-payment-notice-content">
        <p>所选 {applications.length} 条费用已有请款申请，本次没有重复提交。请查看现有请款单继续处理。</p>
        {applications.length !== rows.length && <p>选择中同时包含尚未申请的费用，请分开选择后办理。</p>}
        {groups.map((row) => {
          const number = String(row.data.payment_application_no || "").trim();
          const members = applications.filter((item) => String(item.data.payment_application_no || item.data.internal_application_id || item.serial_no)
            === String(row.data.payment_application_no || row.data.internal_application_id || row.serial_no));
          const statuses = Array.from(new Set(members.map((item) => item.status)));
          const ownApplication = row.data.applicant === username;
          return <section key={row.id}>
            <strong>请款单：{number || row.serial_no}</strong>
            <p>当前状态：{statuses.join("、")}</p>
            {statuses.map((status) => <p key={status}>{status === "待到账" && row.data.commission_lifecycle === "case_agency_fee"
              ? "来源代理费尚未到账，到账后继续后续分配、结算和审批流程。"
              : waitingReasons[status] || "请在现有请款单中查看审批与付款进度。"}</p>)}
            {ownApplication && number && onNavigate && <Button onClick={() => {
              rememberInternalApplicationQuery(number, caseRecord.serial_no);
              onNavigate("finance-internal-mine");
              notice.destroy();
            }}>查看请款单</Button>}
          </section>;
        })}
      </div>,
    });
    return null;
  }
  const payees = rows.map((row) => String(row.data.payment_payee || row.data.payee || "").trim());
  if (payees.some((payee) => !payee) || new Set(payees).size !== 1) throw new Error("请选择同一收款人的内部费用；收款人缺失时请先完善费用");
  return rows.map((row) => {
    if (!["草稿", "已退回", "已审批", "部分付款"].includes(row.status)) throw new Error(`费用 ${row.serial_no} 当前状态“${row.status}”不能申请付款`);
    const total = amount(row.data.amount, "费用金额");
    const requested = amount(row.data.payment_requested_amount, "已申请金额", true);
    const paid = amount(row.data.paid_amount, "已付款金额", true);
    if (total <= 0 || requested < 0 || paid < 0) throw new Error(`费用 ${row.serial_no} 金额不符合付款申请条件`);
    const remaining = Math.round((total - Math.max(requested, paid)) * 100) / 100;
    if (remaining <= 0) throw new Error(`费用 ${row.serial_no} 已申请或没有可申请付款的余额，请勿重复申请`);
    return { ...row, data: { ...row.data, payment_remaining_amount: remaining } };
  });
}

/** 仅处理内部费用步骤；部分成功时移除已确认提交项，保留其余明细和输入。 */
export async function submitPreparedInternalPayments(context: Pick<CaseFinanceDependencies,
  "createdCaseFees" | "caseFeePaymentDrafts" | "caseFeeSubmitting" | "setCaseFeeSubmitting" | "feeCase"
  | "closeCaseFeeCreator" | "load" | "viewingCounselCase" | "openCounselDetail" | "setCreatedCaseFees" | "setCaseFeePaymentDrafts"
>): Promise<void> {
  const { createdCaseFees: rows, caseFeePaymentDrafts: drafts, caseFeeSubmitting, setCaseFeeSubmitting,
    feeCase, closeCaseFeeCreator, load, viewingCounselCase, openCounselDetail, setCreatedCaseFees, setCaseFeePaymentDrafts } = context;
  if (caseFeeSubmitting || !rows.length) return;
  if (rows.length !== drafts.length) return void message.warning("付款申请明细已变化，请关闭后重新选择");
  if (drafts.some((draft) => !draft.payment_payee?.trim() || !draft.payment_account?.trim()))
    return void message.warning("请输入内部费用收款人和付款账号");
  if (new Set(drafts.map((draft) => draft.payment_payee!.trim())).size !== 1)
    return void message.warning("请选择同一收款人的内部费用申请付款");
  try {
    rows.forEach((row) => {
      if (amount(row.data.payment_remaining_amount ?? row.data.amount, "申请金额") <= 0)
        throw new Error(`费用 ${row.serial_no} 没有可申请付款的余额`);
    });
  } catch (error) {
    return void message.warning(error instanceof Error ? error.message : "申请金额无效");
  }
  setCaseFeeSubmitting(true);
  const completed = new Set<number>();
  try {
    for (const [index, row] of rows.entries()) {
      const draft = drafts[index];
      await api.post(`/finance/fees/${row.id}/submit`, {
        amount: Number(row.data.payment_remaining_amount ?? row.data.amount),
        payment_payee: draft.payment_payee!.trim(), payment_account: draft.payment_account!.trim(),
        payment_remark: String(draft.payment_remark || "").trim(),
        comment: String(draft.payment_remark || `案件 ${feeCase?.serial_no || ""} 申请付款`).trim(),
      });
      completed.add(row.id);
    }
  } catch (error: any) {
    setCreatedCaseFees(rows.filter((row) => !completed.has(row.id)));
    setCaseFeePaymentDrafts(drafts.filter((_, index) => !completed.has(rows[index].id)));
    message.error(`${completed.size ? `已提交 ${completed.size} 条，其余费用未全部提交；` : ""}${error?.response?.data?.detail || "付款申请结果未确认，请刷新核对后再处理"}`);
    return;
  } finally {
    setCaseFeeSubmitting(false);
  }
  message.success(`已提交 ${completed.size} 条付款申请`);
  closeCaseFeeCreator();
  try {
    await load();
    if (viewingCounselCase) await openCounselDetail(viewingCounselCase);
  } catch (error: any) {
    message.error(error?.response?.data?.detail || "付款申请已提交，页面刷新失败，请刷新查看");
  }
}
