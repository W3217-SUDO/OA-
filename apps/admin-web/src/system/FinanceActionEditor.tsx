import { useEffect, useState } from "react";
import { Alert, Checkbox, Modal, Spin, message } from "antd";
import { api } from "../api";
import { FINANCE_ACTIONS, FINANCE_CONFIGURE_ACTION } from "./financeActions";

type FinanceActionState = { username: string; display_name: string; is_admin: boolean; action_keys: string[]; page_action_keys: string[] };

/** 当前账号能不能在员工管理里给别人配置财务编辑、删除（管理者或被授权的人，如范明明）。 */
export const canConfigureFinanceActions = (user: { configured_action_keys?: string[] }) => {
  const keys = user.configured_action_keys || [];
  return keys.includes("*") || keys.includes(FINANCE_CONFIGURE_ACTION);
};

/** 员工管理“财务权限”：只配置某人的 6 个财务编辑、删除动作，不涉及其他权限。 */
export function FinanceActionEditor({ username, onClose }: { username: string | null; onClose: () => void }) {
  const [state, setState] = useState<FinanceActionState | null>(null);
  const [checked, setChecked] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!username) return;
    const controller = new AbortController();
    setState(null);
    setError("");
    setLoading(true);
    api.get<FinanceActionState>(`/system/finance-actions/${encodeURIComponent(username)}`, { signal: controller.signal })
      .then(({ data }) => { setState(data); setChecked(data.action_keys); })
      .catch((failure: any) => { if (!controller.signal.aborted) setError(failure?.response?.data?.detail || "财务权限加载失败"); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [username]);

  const save = async () => {
    if (!state) return;
    setSaving(true);
    try {
      const { data } = await api.put<{ action_keys: string[] }>(`/system/finance-actions/${encodeURIComponent(state.username)}`, { action_keys: checked });
      setChecked(data.action_keys);
      message.success("财务权限已保存，对方重新登录或刷新后生效");
      onClose();
    } catch (failure: any) {
      setError(failure?.response?.data?.detail || "财务权限保存失败");
    } finally {
      setSaving(false);
    }
  };

  const pageLabels = FINANCE_ACTIONS.filter((item) => state?.page_action_keys.includes(item.value)).map((item) => item.label);
  return <Modal open={Boolean(username)} title={`财务权限：${state?.display_name || username || ""}`} okText="保存" cancelText="取消"
    confirmLoading={saving} okButtonProps={{ disabled: !state || state.is_admin }} onOk={() => void save()} onCancel={onClose} destroyOnHidden>
    {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 12 }} />}
    <Spin spinning={loading}>
      {state && (state.is_admin
        ? <Alert type="info" showIcon title="管理者默认拥有全部财务权限，不需要配置。" />
        : <>
          <div style={{ marginBottom: 8, color: "var(--oa-text-secondary, #666)" }}>
            {pageLabels.length ? `能打开对应财务页面，默认已有：${pageLabels.join("、")}；取消勾选即不给。` : "当前没有对应的财务页面，勾选后单独开通。"}
          </div>
          <Checkbox.Group options={FINANCE_ACTIONS} value={checked} disabled={saving}
            onChange={(values) => setChecked(values as string[])} />
        </>)}
    </Spin>
  </Modal>;
}
