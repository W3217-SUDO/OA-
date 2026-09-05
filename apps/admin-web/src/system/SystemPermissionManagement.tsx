import {
  Alert,
  Button,
  Card,
  Form,
  Modal,
  Select,
  Table,
  TreeSelect,
} from "antd";
import type { RolePermission, MenuRow } from "./types";
import { formatTime } from "./constants";
import { buildMenuTreeData } from "./SystemMenuManagement";

interface SystemPermissionManagementProps {
  rolePermissions: RolePermission[];
  availableFieldKeys: string[];
  menus: MenuRow[];
  roleOpen: boolean;
  editingRole: RolePermission | null;
  loading: boolean;
  roleForm: ReturnType<typeof Form.useForm>[0];
  onEditRole: (row: RolePermission) => void;
  onSaveRole: () => void;
  onRoleOpenChange: (open: boolean) => void;
}

export function SystemPermissionManagement({
  rolePermissions,
  availableFieldKeys,
  menus,
  roleOpen,
  editingRole,
  loading,
  roleForm,
  onEditRole,
  onSaveRole,
  onRoleOpenChange,
}: SystemPermissionManagementProps) {
  const menuTreeData = buildMenuTreeData(menus);

  return (
    <>
      <Card className="panel system-focused" title="系统角色权限">
        <Alert
          type="warning"
          showIcon
          message="系统管理员为最高权限，必须保留全部菜单、全部字段和全所数据范围。"
          style={{ marginBottom: 12 }}
        />
        <Table
          rowKey="role"
          size="small"
          loading={loading}
          dataSource={rolePermissions}
          pagination={false}
          columns={[
            { title: "角色", dataIndex: "display_name", width: 140 },
            { title: "角色代码", dataIndex: "role", width: 110 },
            { title: "数据范围", dataIndex: "data_scope", width: 130 },
            {
              title: "菜单权限",
              dataIndex: "menu_keys",
              render: (value: string[]) => `${value.length} 项`,
            },
            {
              title: "字段权限",
              dataIndex: "field_keys",
              width: 110,
              render: (value: string[]) => `${value.length} 项`,
            },
            {
              title: "更新时间",
              dataIndex: "updated_at",
              width: 165,
              render: formatTime,
            },
            {
              title: "操作",
              key: "action",
              width: 90,
              render: (_v: unknown, row: RolePermission) => (
                <Button type="link" onClick={() => onEditRole(row)}>
                  权限设定
                </Button>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        open={roleOpen}
        title={`角色维护：${editingRole?.display_name || ""}`}
        okText="保存权限"
        cancelText="取消"
        onOk={onSaveRole}
        onCancel={() => onRoleOpenChange(false)}
        okButtonProps={{ disabled: editingRole?.role === "admin" }}
        destroyOnHidden
        width={760}
      >
        <Form
          form={roleForm}
          layout="vertical"
          disabled={editingRole?.role === "admin"}
        >
          <Form.Item
            name="data_scope"
            label="数据范围"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { value: "全所数据", label: "全所数据" },
                { value: "本部门数据", label: "本部门数据" },
                { value: "授权审批数据", label: "授权审批数据" },
                { value: "本人及共享数据", label: "本人及共享数据" },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="menu_keys"
            label="菜单权限"
            rules={[{ required: true }]}
          >
            <TreeSelect
              treeData={menuTreeData}
              treeCheckable
              treeDefaultExpandAll
              showCheckedStrategy={TreeSelect.SHOW_ALL}
              disabled={editingRole?.role === "admin"}
            />
          </Form.Item>
          <Form.Item
            name="field_keys"
            label="字段权限"
            rules={[{ required: true }]}
          >
            <Select
              mode="multiple"
              options={availableFieldKeys.map((value) => ({
                value,
                label: value,
              }))}
            />
          </Form.Item>
          {editingRole?.role === "admin" && (
            <Alert
              type="info"
              showIcon
              message="系统管理员权限由系统锁定为全部权限，不允许降权。"
            />
          )}
        </Form>
      </Modal>
    </>
  );
}
