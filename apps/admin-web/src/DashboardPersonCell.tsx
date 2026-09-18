import { Tooltip } from "antd";

export default function DashboardPersonCell({ value }: { value?: string }) {
  const names = (value || "").split(/[、,，;；\n]+/).map((name) => name.trim()).filter(Boolean);
  return (
    <Tooltip title={names.join("、")} trigger={["hover", "focus"]}>
      <span className="dashboard-person-cell" tabIndex={names.length ? 0 : undefined}>
        {names[0] || "—"}
      </span>
    </Tooltip>
  );
}
