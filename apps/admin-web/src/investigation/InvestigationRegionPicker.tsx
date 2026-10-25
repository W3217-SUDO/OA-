import { POPUP_WIDTH } from "../components/common/popupSize";
import { useState } from "react";
import { Button, Checkbox, Empty, Input, Modal } from "antd";
import { EnvironmentOutlined } from "@ant-design/icons";
import "./investigation-region-picker.css";

type RegionOption = { value: string; label: string; children: { value: string; label: string }[] };
type Props = { value?: string[][]; onChange?: (value: string[][]) => void; options: RegionOption[]; id?: string };

export function InvestigationRegionPicker({ value = [], onChange, options, id }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<string[][]>([]);
  const [search, setSearch] = useState("");
  const selectedCities = (paths: string[][], province: RegionOption) => province.children
    .filter((city) => paths.some((path) => path[0] === province.value && (path.length === 1 || path[1] === city.value)))
    .map((city) => city.value);
  const replaceProvince = (province: RegionOption, cities: string[]) => {
    setDraft((current) => [
      ...current.filter((path) => path[0] !== province.value),
      ...cities.map((city) => [province.value, city]),
    ]);
  };
  const keyword = search.trim().toLocaleLowerCase();
  const groups = options.filter((province) => !keyword || province.label.toLocaleLowerCase().includes(keyword)
    || province.children.some((city) => city.label.toLocaleLowerCase().includes(keyword)));
  const summary = value.map((path) => path.join(" / ")).join("、");
  return <>
    <Button id={id} className="investigation-region-trigger" icon={<EnvironmentOutlined />} aria-haspopup="dialog" aria-expanded={open} title={summary}
      onClick={() => {
        // 展开历史整省值为当前授权城市，避免部分授权被误提交为整省。
        setDraft(options.flatMap((province) => selectedCities(value, province).map((city) => [province.value, city])));
        setSearch(""); setOpen(true);
      }}>{summary || "请选择调查区域"}</Button>
    <Modal open={open} title="选择调查区域" rootClassName="investigation-region-modal" width={POPUP_WIDTH.lg} okText="确定" cancelText="取消"
      okButtonProps={{ disabled: draft.length === 0 }} onCancel={() => setOpen(false)}
      onOk={() => { onChange?.(draft); setOpen(false); }} destroyOnHidden>
      <Input.Search allowClear placeholder="搜索省份或城市" aria-label="搜索调查区域" value={search} onChange={(event) => setSearch(event.target.value)} />
      <div className="investigation-region-toolbar">
        <span>已选 {draft.length} 个城市</span>
        <Button onClick={() => setDraft(options.flatMap((province) => province.children.map((city) => [province.value, city.value])))}>全选授权区域</Button>
        <Button onClick={() => setDraft([])}>清空</Button>
      </div>
      <div className="investigation-region-groups">
        {groups.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有匹配的授权区域" />}
        {groups.map((province) => {
          const selected = selectedCities(draft, province);
          return <section key={province.value} className="investigation-region-group" aria-label={province.label}>
            <Checkbox checked={selected.length === province.children.length} indeterminate={selected.length > 0 && selected.length < province.children.length}
              onChange={(event) => replaceProvince(province, event.target.checked ? province.children.map((city) => city.value) : [])}>{province.label}</Checkbox>
            <Checkbox.Group value={selected} onChange={(cities) => replaceProvince(province, cities)}
              options={province.children.map((city) => ({ value: city.value, label: city.label }))} />
          </section>;
        })}
      </div>
    </Modal>
  </>;
}
