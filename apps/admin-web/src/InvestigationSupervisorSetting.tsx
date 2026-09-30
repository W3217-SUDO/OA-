import { useEffect, useState } from "react";
import { Alert, Button, Modal, Select, Spin, message } from "antd";
import { api } from "./api";

type SupervisorOption = { username: string; display_name: string };

export default function InvestigationSupervisorSetting() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [username, setUsername] = useState<string>();
  const [options, setOptions] = useState<SupervisorOption[]>([]);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setOptions([]);
    setUsername(undefined);
    api.get("/system/configs", { params: { keyword: "investigation_assignment" }, signal: controller.signal })
      .then(({ data }) => {
        if (controller.signal.aborted) return;
        const config = data.items.find((item: { key: string }) => item.key === "investigation_assignment");
        if (!config) throw new Error("调查任务分配配置不存在");
        setUsername(config.value.supervisor_username || undefined);
        setOptions(data.investigation_supervisor_options);
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err?.response?.data?.detail || err.message || "配置加载失败");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [open, reload]);

  const save = async () => {
    setSaving(true);
    try {
      await api.patch("/system/configs/investigation_assignment", { value: { supervisor_username: username || "" } });
      message.success(username ? "调查任务分配人员已更新" : "调查任务分配人员已清除");
      setOpen(false);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || "配置保存失败");
    } finally {
      setSaving(false);
    }
  };

  return <>
    <Button onClick={() => setOpen(true)}>配置调查任务分配人员</Button>
    <Modal title="调查任务分配人员" open={open} confirmLoading={saving}
      okText="保存配置" cancelText="取消" okButtonProps={{ disabled: loading || Boolean(error) }}
      cancelButtonProps={{ disabled: saving }} closable={!saving} maskClosable={!saving}
      onCancel={() => setOpen(false)} onOk={() => void save()} destroyOnHidden>
      {error ? <Alert type="error" showIcon message={error} action={<Button onClick={() => setReload((value) => value + 1)}>重试</Button>} /> :
        <Spin spinning={loading}>
          <p>新建调查任务统一交给此人员，由其继续分配调查子任务。</p>
          <Select aria-label="调查任务分配人员" allowClear showSearch optionFilterProp="label"
            style={{ width: "100%" }} placeholder="请选择调查主管" value={username} onChange={setUsername}
            options={options.map((item) => ({ value: item.username, label: `${item.display_name || "姓名待维护"}（${item.username}）` }))} />
          <p>清除后需重新配置才能新建调查任务。更换人员不改变已有任务的负责人。</p>
        </Spin>}
    </Modal>
  </>;
}
