import { useState } from "react";
import { Button, Descriptions, Modal, Table } from "antd";

export function CommissionPerson({ row }: { row: any }) {
  const [open, setOpen] = useState(false);
  return <>
    <Button type="link" size="small" onClick={() => setOpen(true)}>{row.employee_display_name}</Button>
    <Modal title="提成查看" open={open} footer={<Button onClick={() => setOpen(false)}>取消</Button>} onCancel={() => setOpen(false)} width={600}>
      <Descriptions size="small" column={1} items={[
        { key: "name", label: "人员", children: row.employee_display_name },
        { key: "date", label: "有效日期", children: `${row.scheme_start_date || "—"} 至 ${row.scheme_end_date || "长期"}` },
      ]} />
      <Table size="small" pagination={false} rowKey="role" dataSource={row.scheme_details || []}
        locale={{ emptyText: "未找到对应提成方案，请重新打开新增提成" }}
        columns={[{ title: "提成类型", dataIndex: "role" }, { title: "固定比例", dataIndex: "rate", render: (n: number) => `${Number((n * 100).toFixed(4))}%` }, { title: "固定金额", dataIndex: "fixed" }]} />
    </Modal>
  </>;
}
