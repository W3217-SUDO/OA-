import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
} from "antd";
import { ReloadOutlined, PlusOutlined } from "@ant-design/icons";
import type { SystemUser } from "./types";
import {
  formatTime,
  PERSON_NAME_PLACEHOLDER,
  personDisplayName,
} from "./constants";

interface SystemUserManagementProps {
  users: SystemUser[];
  keyword: string;
  loading: boolean;
  userOpen: boolean;
  editingUser: SystemUser | null;
  resettingUser: SystemUser | null;
  userDepartmentOptions: { value: string; label: string }[];
  userForm: ReturnType<typeof Form.useForm>[0];
  resetPasswordForm: ReturnType<typeof Form.useForm>[0];
  onKeywordChange: (value: string) => void;
  onLoadUsers: (keyword: string) => void;
  onEditUser: (row?: SystemUser) => void;
  onSaveUser: () => void;
  onRemoveUser: (row: SystemUser) => void;
  onUserOpenChange: (open: boolean) => void;
  onOpenPasswordReset: (row: SystemUser) => void;
  onResetPassword: () => void;
  onResetPasswordClose: () => void;
  onUnlockUser: (row: SystemUser) => void;
}

export function SystemUserManagement({
  users,
  keyword,
  loading,
  userOpen,
  editingUser,
  resettingUser,
  userDepartmentOptions,
  userForm,
  resetPasswordForm,
  onKeywordChange,
  onLoadUsers,
  onEditUser,
  onSaveUser,
  onRemoveUser,
  onUserOpenChange,
  onOpenPasswordReset,
  onResetPassword,
  onResetPasswordClose,
  onUnlockUser,
}: SystemUserManagementProps) {
  const renderPersonDisplayName = (_value: string, row: SystemUser) => {
    const name = personDisplayName(row);
    if (name !== PERSON_NAME_PLACEHOLDER) return name;
    return (
      <Tooltip title="请在修改入口补充姓名">
        <Tag color="orange">{name}</Tag>
      </Tooltip>
    );
  };

  return (
    <>
      <Card className="panel system-focused" title="系统用户管理">
        <div className="system-query">
          <label>
            <span>账号/姓名</span>
            <Input
              value={keyword}
              onChange={(e) => onKeywordChange(e.target.value)}
              onPressEnter={() => onLoadUsers(keyword)}
              allowClear
            />
          </label>
          <Button type="primary" onClick={() => onLoadUsers(keyword)}>
            查询
          </Button>
          <Tooltip title="刷新系统用户">
            <Button
              aria-label="刷新系统用户"
              icon={<ReloadOutlined />}
              onClick={() => onLoadUsers(keyword)}
            />
          </Tooltip>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => onEditUser()}
          >
            新增账号
          </Button>
        </div>
        <Alert
          type="info"
          showIcon
          message="合同审批人由管理员逐人加入合同审批流程；岗位名称或系统角色不会自动授予审批资格。"
          style={{ marginBottom: 12 }}
        />
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={users}
          pagination={{
            defaultPageSize: 15,
            showSizeChanger: true,
            pageSizeOptions: ["10", "15", "20", "50", "100", "200"],
            showQuickJumper: { goButton: "GO" },
            showTotal: (total) => `共 ${total} 个账号`,
          }}
          locale={{
            emptyText: (
              <span>
                没有查询到符合条件的记录，可以去
                <Button type="link" size="small" onClick={() => onEditUser()}>
                  新增用户
                </Button>
                。
              </span>
            ),
          }}
          columns={[
            { title: "登录账号", dataIndex: "username", width: 130 },
            { title: "姓名", dataIndex: "display_name", width: 130, render: renderPersonDisplayName },
            { title: "部门", dataIndex: "department", width: 140 },
            { title: "Email", dataIndex: "email", width: 180 },
            { title: "手机号码", dataIndex: "mobile", width: 130 },
            { title: "固定电话", dataIndex: "office_phone", width: 130 },
            {
              title: "钉钉",
              dataIndex: "dingtalk_bound",
              width: 90,
              render: (value: boolean) => <Tag color={value ? "blue" : "default"}>{value ? "已绑定" : "未绑定"}</Tag>,
            },
            {
              title: "系统角色",
              dataIndex: "role",
              width: 105,
              render: (_value: string, row: SystemUser) => {
                const roles = row.role_ids?.length ? row.role_ids : [row.role];
                return (
                  <Space size={[0, 4]} wrap>
                    {roles.map((value) => (
                      <Tag
                        key={value}
                        color={
                          value === "admin"
                            ? "red"
                            : value === "manager"
                              ? "blue"
                              : "default"
                        }
                      >
                        {value === "admin"
                          ? "系统管理员"
                          : value === "manager"
                            ? "部门负责人"
                            : value === "auditor"
                              ? "审计人员"
                              : "普通用户"}
                      </Tag>
                    ))}
                  </Space>
                );
              },
            },
            {
              title: "合同审批流程",
              dataIndex: "contract_approval_enabled",
              width: 120,
              render: (value: boolean) => (
                <Tag color={value ? "green" : "default"}>
                  {value ? "已配置" : "未配置"}
                </Tag>
              ),
            },
            {
              title: "状态",
              dataIndex: "is_active",
              width: 80,
              render: (value: boolean) => (
                <Tag color={value ? "green" : "default"}>
                  {value ? "可用" : "停用"}
                </Tag>
              ),
            },
            {
              title: "失败次数",
              dataIndex: "failed_login_attempts",
              width: 85,
            },
            {
              title: "锁定至",
              dataIndex: "locked_until",
              width: 165,
              render: formatTime,
            },
            {
              title: "最后登录",
              dataIndex: "last_login_at",
              width: 165,
              render: formatTime,
            },
            {
              title: "操作",
              key: "action",
              width: 250,
              render: (_v: unknown, row: SystemUser) => (
                <Space size={0} wrap>
                  <Button type="link" onClick={() => onEditUser(row)}>
                    修改
                  </Button>
                  <Button
                    type="link"
                    onClick={() => onOpenPasswordReset(row)}
                  >
                    重置密码
                  </Button>
                  <Button
                    type="link"
                    disabled={!row.failed_login_attempts && !row.locked_until}
                    onClick={() => onUnlockUser(row)}
                  >
                    解锁
                  </Button>
                  {row.role !== "admin" && !row.role_ids?.includes("admin") && (
                    <Popconfirm
                      title="确认删除该登录账号？"
                      onConfirm={() => onRemoveUser(row)}
                    >
                      <Button type="link" danger>
                        删除
                      </Button>
                    </Popconfirm>
                  )}
                </Space>
              ),
            },
          ]}
          scroll={{ x: 1440 }}
        />
      </Card>
      <Modal
        open={userOpen}
        title={editingUser ? "修改系统账号" : "新增系统账号"}
        okText="保存"
        cancelText="取消"
        onOk={onSaveUser}
        onCancel={() => onUserOpenChange(false)}
        destroyOnHidden
        width={680}
      >
        <Form form={userForm} layout="vertical">
          <div className="system-modal-grid">
            <Form.Item
              label="登录账号"
              name="username"
              rules={[{ required: true }, { min: 3 }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="姓名"
              name="display_name"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="部门"
              name="department"
              rules={[{ required: true }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="请选择部门"
                options={userDepartmentOptions}
              />
            </Form.Item>
            <Form.Item label="钉钉 UserId" name={["profile", "dingtalk_user_id"]} tooltip="在钉钉开发者后台的通讯录中查看；每个 UserId 只能绑定一个系统员工。">
              <Input allowClear placeholder="留空表示未绑定" />
            </Form.Item>
            <Form.Item
              label={
                editingUser
                  ? "新密码（留空不修改；填写后用户须首次改密）"
                  : "一次性初始密码"
              }
              name="password"
              rules={editingUser ? [] : [{ required: true }, { min: 8 }]}
            >
              <Input.Password />
            </Form.Item>
            <Form.Item
              label="系统角色"
              name="role"
              rules={[{ required: true }]}
              hidden
            >
              <Select
                options={[
                  { value: "admin", label: "系统管理员（最高权限）" },
                  { value: "manager", label: "部门负责人" },
                  { value: "auditor", label: "审计人员" },
                  { value: "user", label: "普通用户" },
                ]}
              />
            </Form.Item>
            <Form.Item
              label="系统角色（可多选）"
              name="role_ids"
              rules={[{ required: true, message: "请至少选择一个系统角色" }]}
            >
              <Select
                mode="multiple"
                placeholder="请选择系统角色"
                options={[
                  { value: "admin", label: "系统管理员（最高权限）" },
                  { value: "manager", label: "部门负责人" },
                  { value: "auditor", label: "审计人员" },
                  { value: "user", label: "普通用户" },
                ]}
              />
            </Form.Item>
            <Form.Item
              label="是否可用"
              name="is_active"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
            <Form.Item
              label="合同审批流程人员"
              name={["profile", "contract_approval_enabled"]}
              valuePropName="checked"
            >
              <Switch checkedChildren="是" unCheckedChildren="否" />
            </Form.Item>
            <Form.Item label="Email" name={["profile", "email"]}>
              <Input />
            </Form.Item>
            <Form.Item label="手机" name={["profile", "mobile"]}>
              <Input />
            </Form.Item>
            <Form.Item label="办公电话" name={["profile", "office_phone"]}>
              <Input />
            </Form.Item>
          </div>
        </Form>
      </Modal>
      <Modal
        open={Boolean(resettingUser)}
        title={`重置密码：${personDisplayName(resettingUser || undefined)}`}
        okText="确认重置"
        cancelText="取消"
        onOk={onResetPassword}
        onCancel={onResetPasswordClose}
        destroyOnHidden
      >
        <Alert
          type="warning"
          showIcon
          message="重置后将解除登录锁定，且该账号下次登录必须修改密码。"
          style={{ marginBottom: 16 }}
        />
        <Form form={resetPasswordForm} layout="vertical">
          <Form.Item
            label="临时新密码"
            name="new_password"
            rules={[
              { required: true, message: "请输入临时新密码" },
              { min: 8, message: "密码至少 8 位" },
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            label="确认临时新密码"
            name="confirm_password"
            dependencies={["new_password"]}
            rules={[
              { required: true, message: "请再次输入临时新密码" },
              {
                validator: (_rule, value) =>
                  !value ||
                  value === resetPasswordForm.getFieldValue("new_password")
                    ? Promise.resolve()
                    : Promise.reject(new Error("两次密码输入不一致")),
              },
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
