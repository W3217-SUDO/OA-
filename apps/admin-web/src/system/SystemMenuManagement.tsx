import { useMemo } from "react";
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
} from "antd";
import { EditOutlined, PlusOutlined } from "@ant-design/icons";
import type { MenuRow } from "./types";

interface SystemMenuManagementProps {
  menus: MenuRow[];
  menuPage: number;
  menuPageSize: number;
  menuJumpPage: string;
  menuSearchInput: string;
  menuSearch: string;
  menuOpen: boolean;
  editingMenu: MenuRow | null;
  loading: boolean;
  menuForm: ReturnType<typeof Form.useForm>[0];
  onMenuSearchInputChange: (value: string) => void;
  onMenuSearch: (value: string) => void;
  onMenuPageChange: (page: number, pageSize: number) => void;
  onMenuJumpPageChange: (value: string) => void;
  onJumpToMenuPage: () => void;
  onEditMenu: (row: MenuRow) => void;
  onSaveMenu: () => void;
  onRemoveMenu: (row: MenuRow) => void;
  onMenuOpenChange: (open: boolean) => void;
  onNewMenu: () => void;
  onResetMenuSearch: () => void;
}

export function SystemMenuManagement({
  menus,
  menuPage,
  menuPageSize,
  menuJumpPage,
  menuSearchInput,
  menuSearch,
  menuOpen,
  editingMenu,
  loading,
  menuForm,
  onMenuSearchInputChange,
  onMenuSearch,
  onMenuPageChange,
  onMenuJumpPageChange,
  onJumpToMenuPage,
  onEditMenu,
  onSaveMenu,
  onRemoveMenu,
  onMenuOpenChange,
  onNewMenu,
  onResetMenuSearch,
}: SystemMenuManagementProps) {
  const systemMenus = menus.filter((row) => row.is_system),
    legacyMenus = menus.filter((row) => !row.is_system);
  const normalizedMenuSearch = menuSearch.trim().toLowerCase();
  const filteredSystemMenus = normalizedMenuSearch
    ? systemMenus.filter((row) => [row.key, row.parent_key, row.label, row.description].join(" ").toLowerCase().includes(normalizedMenuSearch))
    : systemMenus;

  const menuTreeData = useMemo(() => {
    const nodes = new Map<string, any>();
    menus.forEach((row) =>
      nodes.set(row.key, {
        title: row.label,
        value: row.key,
        key: row.key,
        children: [],
      }),
    );
    const roots: any[] = [];
    menus.forEach((row) => {
      const node = nodes.get(row.key);
      const parent = row.parent_key ? nodes.get(row.parent_key) : undefined;
      if (parent) parent.children.push(node);
      else roots.push(node);
    });
    return roots;
  }, [menus]);

  return (
    <>
      <Card className="panel system-focused" title="菜单列表">
        <Alert
          type="info"
          showIcon
          message="无路由菜单作为目录/权限节点，不会导航到页面；有路由菜单仅允许已实现路由。"
          style={{ marginBottom: 12 }}
        />
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={onNewMenu}
        >
          新增菜单
        </Button>
        <Space wrap style={{ margin: "12px 0" }}>
          <Input value={menuSearchInput} placeholder="菜单名称/标识" onChange={(event) => onMenuSearchInputChange(event.target.value)} style={{ width: 220 }} />
          <Button onClick={() => onMenuSearch(menuSearchInput)}>查询</Button>
          <Button onClick={onResetMenuSearch}>重置</Button>
        </Space>
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          columns={[
            {
              title: "序号",
              key: "no",
              width: 70,
              render: (_v: unknown, _r: unknown, i: number) => i + 1,
            },
            { title: "菜单标识", dataIndex: "key", width: 240 },
            {
              title: "父级标识",
              dataIndex: "parent_key",
              width: 220,
              render: (value: string) => value || "—",
            },
            { title: "菜单名称", dataIndex: "label" },
            { title: "菜单描述", dataIndex: "description" },
            {
              title: "操作",
              key: "action",
              width: 100,
              render: (_v: unknown, row: MenuRow) => (
                <Button
                  type="link"
                  icon={<EditOutlined />}
                  onClick={() => onEditMenu(row)}
                >
                  修改
                </Button>
              ),
            },
          ]}
          dataSource={filteredSystemMenus}
          locale={{ emptyText: "没有查询到符合条件的记录，可以去新增菜单。" }}
          pagination={{
            current: menuPage,
            pageSize: menuPageSize,
            total: filteredSystemMenus.length,
            showSizeChanger: true,
            pageSizeOptions: ["10", "15", "20", "30", "50", "100", "200"],
            showQuickJumper: true,
            onChange: (page, size) => { onMenuPageChange(page, size); },
            showTotal: (total) => `共 ${total} 项`,
          }}
          scroll={{ x: 1100 }}
        />
        <Space size="small" style={{ float: "right", marginTop: -40, marginRight: 8 }}>
          <Input
            aria-label="菜单页码"
            value={menuJumpPage}
            onChange={(event) => onMenuJumpPageChange(event.target.value.replace(/\D/g, ""))}
            onPressEnter={onJumpToMenuPage}
            placeholder="页码"
            size="small"
            style={{ width: 64 }}
          />
          <Button size="small" onClick={onJumpToMenuPage}>GO</Button>
        </Space>
      </Card>
      {legacyMenus.length > 0 && (
        <Card
          className="panel system-focused"
          title="未纳入当前导航的历史菜单"
          style={{ marginTop: 16 }}
        >
          <Table
            rowKey="id"
            size="small"
            columns={[
              { title: "菜单标识", dataIndex: "key" },
              { title: "菜单名称", dataIndex: "label" },
              { title: "菜单描述", dataIndex: "description" },
              {
                title: "操作",
                key: "action",
                width: 120,
                render: (_v: unknown, row: MenuRow) => (
                  <Popconfirm
                    title="确认删除该历史菜单？"
                    onConfirm={() => onRemoveMenu(row)}
                  >
                    <Button type="link" danger>
                      删除
                    </Button>
                  </Popconfirm>
                ),
              },
            ]}
            dataSource={legacyMenus}
            pagination={false}
          />
        </Card>
      )}
      <Modal
        open={menuOpen}
        title={editingMenu ? "修改菜单" : "新增菜单"}
        okText="确定"
        cancelText="取消"
        onOk={onSaveMenu}
        onCancel={() => onMenuOpenChange(false)}
        destroyOnHidden
      >
        <Form form={menuForm} layout="vertical">
          <Form.Item label="菜单标识">
            <Input value={editingMenu?.key || ""} disabled />
          </Form.Item>
          <Form.Item label="父级标识">
            <Input value={editingMenu?.parent_key || "顶级菜单"} disabled />
          </Form.Item>
          <Form.Item label="菜单名称" name="label" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            label="菜单名称描述"
            name="description"
            rules={[{ required: true, message: "请输入菜单名称描述." }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="图标" name="icon">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item
            label="排序号"
            name="sort_order"
            rules={[{ required: true }]}
          >
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="是否显示" name="is_visible" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="是否可用" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

// 导出 menuTreeData 供权限管理使用
export function buildMenuTreeData(menus: MenuRow[]) {
  const nodes = new Map<string, any>();
  menus.forEach((row) =>
    nodes.set(row.key, {
      title: row.label,
      value: row.key,
      key: row.key,
      children: [],
    }),
  );
  const roots: any[] = [];
  menus.forEach((row) => {
    const node = nodes.get(row.key);
    const parent = row.parent_key ? nodes.get(row.parent_key) : undefined;
    if (parent) parent.children.push(node);
    else roots.push(node);
  });
  return roots;
}
