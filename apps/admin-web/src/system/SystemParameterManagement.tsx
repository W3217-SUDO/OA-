import { useMemo } from "react";
import {
  Button,
  Card,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
} from "antd";
import type { TableColumnsType } from "antd";
import {
  ClearOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import type {
  ParameterRow,
  ParameterRelationEditor,
} from "./types";
import {
  categoryTitle,
  categoryPlaceholder,
  extraFields,
  formatTime,
  caseFileTypeParentOptions,
  isCaseFileTypeParentValid,
  feeTypeParentOptions,
  feeTypeTreeRows,
  feeTypeRootName,
  cleanCompanyDigitsInputEvent,
} from "./constants";

interface SystemParameterManagementProps {
  category: string;
  numericCode: boolean;
  parameters: ParameterRow[];
  keyword: string;
  secondaryKeyword: string;
  loading: boolean;
  parameterOpen: boolean;
  editingParameter: ParameterRow | null;
  relationEditor: ParameterRelationEditor | null;
  relationTargetOptions: { value: number; label: string; disabled?: boolean }[];
  selectedRelationTargetIds: number[];
  relationSaving: boolean;
  parameterForm: ReturnType<typeof Form.useForm>[0];
  onKeywordChange: (value: string) => void;
  onSecondaryKeywordChange: (value: string) => void;
  onLoadParameters: () => void;
  onStartParameter: (row?: ParameterRow) => void;
  onSaveParameter: () => void;
  onRemoveParameter: (row: ParameterRow) => void;
  onParameterOpenChange: (open: boolean) => void;
  onOpenParameterRelation: (
    kind: "case-type-file-types" | "file-type-fee-types" | "case-type-case-phases",
    source: ParameterRow,
  ) => void;
  onSaveParameterRelation: () => void;
  onRelationEditorClose: () => void;
  onSelectedRelationTargetIdsChange: (ids: number[]) => void;
}

export function SystemParameterManagement({
  category,
  numericCode,
  parameters,
  keyword,
  secondaryKeyword,
  loading,
  parameterOpen,
  editingParameter,
  relationEditor,
  relationTargetOptions,
  selectedRelationTargetIds,
  relationSaving,
  parameterForm,
  onKeywordChange,
  onSecondaryKeywordChange,
  onLoadParameters,
  onStartParameter,
  onSaveParameter,
  onRemoveParameter,
  onParameterOpenChange,
  onOpenParameterRelation,
  onSaveParameterRelation,
  onRelationEditorClose,
  onSelectedRelationTargetIdsChange,
}: SystemParameterManagementProps) {
  const title = `${categoryTitle[category]}列表`;
  const usesParentCode = ["fee_type", "cause", "case_file_type", "district"].includes(
    category,
  );
  const visibleParameters = parameters.filter(
    (row) =>
      !secondaryKeyword ||
      (category === "court"
        ? row.code.includes(secondaryKeyword)
        : String(row.extra.parent_code || "").includes(secondaryKeyword)),
  );
  const parameterDataSource = category === "fee_type"
    ? feeTypeTreeRows(visibleParameters)
    : visibleParameters;

  const auditColumns = [
    { title: "创建人", dataIndex: "created_by", width: 90 },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 165,
      render: formatTime,
    },
    { title: "修改人", dataIndex: "updated_by", width: 90 },
    {
      title: "修改时间",
      dataIndex: "updated_at",
      width: 165,
      render: formatTime,
    },
  ];

  const actionColumn = {
    title: "操作",
    key: "action",
    width:
      category === "case_type"
        ? 300
        : category === "case_file_type"
          ? 220
          : 120,
    render: (_value: unknown, row: ParameterRow) => (
      <Space size={0}>
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => onStartParameter(row)}
        >
          修改
        </Button>
        {category === "case_type" && (
          <>
            <Button
              type="link"
              onClick={() =>
                onOpenParameterRelation("case-type-file-types", row)
              }
            >
              关联文件类型
            </Button>
            <Button
              type="link"
              onClick={() =>
                onOpenParameterRelation("case-type-case-phases", row)
              }
            >
              关联案件阶段
            </Button>
          </>
        )}
        {category === "case_file_type" && (
          <Button
            type="link"
            onClick={() => onOpenParameterRelation("file-type-fee-types", row)}
          >
            关联费用类型
          </Button>
        )}
        {category !== "case_type" && (
          <Popconfirm title="确认删除？" onConfirm={() => onRemoveParameter(row)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        )}
      </Space>
    ),
  };

  const parameterColumns = useMemo<TableColumnsType<ParameterRow>>(() => {
    if (category === "case_type")
      return [
        { title: "类型编号", dataIndex: "code", width: 120 },
        { title: "类型名称", dataIndex: "name", width: 180 },
        {
          title: "类型字母名称",
          key: "letter",
          width: 140,
          render: (_, r) => r.extra.letter_code || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "fee_type")
      return [
        { title: "类型代码", dataIndex: "code", width: 120 },
        { title: "类型名称", dataIndex: "name", width: 180 },
        {
          title: "类型大类",
          key: "group",
          width: 140,
          render: (_, r) => feeTypeRootName(r, parameters),
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "case_phase")
      return [
        { title: "阶段Id", dataIndex: "code", width: 100 },
        { title: "案件阶段", dataIndex: "name", width: 150 },
        {
          title: "上级阶段Id",
          key: "parent",
          width: 110,
          render: (_, r) => r.extra.parent_code || "—",
        },
        {
          title: "案件类型",
          key: "caseType",
          width: 140,
          render: (_, r) => r.extra.case_type || "—",
        },
        { title: "排序号", dataIndex: "sort_order", width: 80 },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "court")
      return [
        { title: "序号", dataIndex: "sort_order", width: 70 },
        { title: "法院名称", dataIndex: "name", width: 220 },
        { title: "法院代码", dataIndex: "code", width: 140 },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "notary_office")
      return [
        { title: "公证处Id", dataIndex: "code", width: 110 },
        { title: "公证处名称", dataIndex: "name", width: 190 },
        { title: "公证处代码", dataIndex: "code", width: 130 },
        {
          title: "公证号模板",
          key: "template",
          width: 170,
          render: (_, r) => r.extra.number_template || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "cause")
      return [
        { title: "案由Id", dataIndex: "code", width: 100 },
        { title: "案由名称", dataIndex: "name", width: 210 },
        {
          title: "上级案由Id",
          key: "parent",
          width: 120,
          render: (_, r) => r.extra.parent_code || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "ipr_case_file_type")
      return [
        { title: "类型代码", dataIndex: "code", width: 150 },
        { title: "文件类型名称", dataIndex: "name", width: 220 },
        {
          title: "适用案件",
          key: "kinds",
          width: 140,
          render: (_, r) =>
            ((r.extra.case_kinds || []) as string[]).join("、") || "全部",
        },
        {
          title: "待转文",
          key: "transfer",
          width: 90,
          render: (_, r) => (r.extra.requires_transmission ? "是" : "否"),
        },
        {
          title: "允许重复",
          key: "repeat",
          width: 100,
          render: (_, r) => (r.extra.allow_repeat === false ? "否" : "是"),
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "case_file_type")
      return [
        { title: "文件类型代码", dataIndex: "code", width: 150 },
        { title: "文件类型名称", dataIndex: "name", width: 220 },
        {
          title: "上级文件类型代码",
          key: "parent",
          width: 160,
          render: (_, r) => r.extra.parent_code || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "district")
      return [
        { title: "地区代码", dataIndex: "code", width: 150 },
        { title: "地区名称", dataIndex: "name", width: 220 },
        {
          title: "上级地区代码",
          key: "parent",
          width: 150,
          render: (_, r) => r.extra.parent_code || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "customer_type")
      return [
        { title: "类型代码", dataIndex: "code", width: 150 },
        { title: "类型名称", dataIndex: "name", width: 220 },
        { title: "排序号", dataIndex: "sort_order", width: 90 },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "court_officer")
      return [
        { title: "工作人员代码", dataIndex: "code", width: 150 },
        { title: "姓名", dataIndex: "name", width: 150 },
        {
          title: "法院代码",
          key: "court",
          width: 130,
          render: (_, r) => r.extra.court_code || "—",
        },
        {
          title: "职务",
          key: "role",
          width: 110,
          render: (_, r) => r.extra.role || "—",
        },
        {
          title: "联系电话",
          key: "phone",
          width: 150,
          render: (_, r) => r.extra.phone || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    return [
      { title: "序号", dataIndex: "sort_order", width: 70 },
      { title: "付款单位名", dataIndex: "name", width: 160 },
      {
        title: "付款性质",
        key: "nature",
        width: 130,
        render: (_, r) => r.extra.nature || "—",
      },
      {
        title: "收款单位",
        key: "payee",
        width: 190,
        render: (_, r) => r.extra.payee || "—",
      },
      {
        title: "开户行",
        key: "account_bank",
        width: 180,
        render: (_, r) => r.extra.account_bank || r.extra.bank || "—",
      },
      {
        title: "账号信息",
        key: "account",
        width: 190,
        render: (_, r) => r.extra.account || "—",
      },
      actionColumn,
    ];
  }, [category, parameters]);

  const empty = (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
  );

  return (
    <>
      <Card className="panel system-focused" title={title}>
        <div className="system-query">
          <label>
            <span>
              {category === "court"
                ? "法院名称"
                : usesParentCode
                  ? `${categoryTitle[category]}名称`
                  : categoryPlaceholder[category]}
            </span>
            <Input
              value={keyword}
              onChange={(e) => onKeywordChange(e.target.value)}
              onPressEnter={() => onLoadParameters()}
              allowClear
            />
          </label>
          {category === "court" && (
            <label>
              <span>法院代码</span>
              <Input
                value={secondaryKeyword}
                onChange={(e) => onSecondaryKeywordChange(e.target.value)}
                allowClear
              />
            </label>
          )}
          {usesParentCode && (
            <label>
              <span>{category === "cause" ? "上级案由Id" : "上级代码"}</span>
              <Input
                value={secondaryKeyword}
                onChange={(e) => onSecondaryKeywordChange(e.target.value)}
                allowClear
              />
            </label>
          )}
          <Button type="primary" onClick={() => onLoadParameters()}>
            查询
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => onStartParameter()}
          >
            {category === "payment_type"
              ? "新增付款单位"
              : `新增${categoryTitle[category]}`}
          </Button>
        </div>
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          columns={parameterColumns}
          dataSource={parameterDataSource}
          locale={{
            emptyText: (
              <span>
                没有查询到符合条件的记录，可以去
                <Button type="link" size="small" onClick={() => onStartParameter()}>
                  {category === "payment_type"
                    ? "新增付款单位"
                    : `新增${categoryTitle[category]}`}
                </Button>
                。
              </span>
            ),
          }}
          pagination={{
            defaultPageSize: 15,
            showSizeChanger: true,
            pageSizeOptions: ["10", "15", "20", "50", "100", "200"],
            showTotal: (total) => `共 ${total} 条`,
          }}
          scroll={{ x: 1100 }}
        />
      </Card>

      <Modal
        open={parameterOpen}
        title={category === "payment_type"
          ? `${editingParameter ? "修改" : "新增"}付款单位`
          : `${editingParameter ? "修改" : "新增"}${categoryTitle[category] || "参数"}`}
        okText="保存"
        cancelText="取消"
        onOk={onSaveParameter}
        onCancel={() => onParameterOpenChange(false)}
        destroyOnHidden
      >
        <Form form={parameterForm} layout="vertical">
          {category === "payment_type" ? (
            <div className="system-modal-grid payment-unit-modal-grid">
              <Form.Item label="性质" name="nature" rules={[{ required: true, message: "请选择性质" }]}>
                <Select options={["官费", "其他费用", "代理费", "对公", "个人"].map((value) => ({ value, label: value }))} />
              </Form.Item>
              <Form.Item label="收款单位" name="payee" rules={[{ required: true, message: "请输入收款单位" }]}>
                <Input />
              </Form.Item>
              <Form.Item label="开户行" name="account_bank" rules={[{ required: true, message: "请输入开户行" }]}>
                <Input />
              </Form.Item>
              <Form.Item label="账号信息" name="account" rules={[{ required: true, message: "请输入账号信息" }]}>
                <Input.TextArea rows={4} maxLength={1000} showCount />
              </Form.Item>
            </div>
          ) : (
          <div className="system-modal-grid">
            <Form.Item
              label={category === "case_type" ? "类型字母名称" : category === "fee_type" ? "类型ID" : "代码"}
              name="code"
              rules={[
                {
                  required: true,
                  message:
                    category === "case_type"
                      ? "请输入类型字母名称."
                      : undefined,
                },
              ]}
            >
              <Input
                inputMode={numericCode ? "numeric" : undefined}
                maxLength={numericCode ? 7 : undefined}
                onInput={
                  numericCode ? cleanCompanyDigitsInputEvent : undefined
                }
              />
            </Form.Item>
            <Form.Item
              label={
                category === "case_type"
                  ? "类型名称"
                  : category === "cause"
                    ? "案由名称"
                    : "名称"
              }
              name="name"
              rules={[
                {
                  required: true,
                  message:
                    category === "case_type"
                      ? "请输入类型名称."
                      : category === "cause"
                        ? "请输入案由名称."
                        : undefined,
                },
              ]}
            >
              <Input />
            </Form.Item>
            {(extraFields[category] || []).map((item) => {
              const isFeeTypeParent = category === "fee_type" && item.key === "parent_code";
              const numericParent = item.key === "parent_code" && !isFeeTypeParent;
              const isCaseFileTypeParent =
                category === "case_file_type" && item.key === "parent_code";
              return (
                <Form.Item
                  key={item.key}
                  label={item.label}
                  name={item.key}
                  rules={
                    isCaseFileTypeParent || isFeeTypeParent
                      ? [
                          {
                            validator: async (_, value) => {
                              const valid = isFeeTypeParent
                                ? !value || feeTypeParentOptions(parameters, editingParameter?.id).some((option) => option.value === value)
                                : isCaseFileTypeParentValid(value, parameters, editingParameter?.id);
                              if (valid) return;
                              throw new Error(isFeeTypeParent
                                ? "请选择有效的上级费用类型，且不能选择自身或下级"
                                : "请选择有效的上级文件类型，且不能选择自身");
                            },
                          },
                        ]
                      : category === "payment_type"
                        ? [{ required: true, message: `请输入${item.label}` }]
                        : undefined
                  }
                >
                  {isCaseFileTypeParent || isFeeTypeParent ? (
                    <Select
                      allowClear
                      showSearch
                      optionFilterProp="label"
                      placeholder={isFeeTypeParent ? "不选择表示新增费用大类" : "请选择上级文件类型"}
                      options={isFeeTypeParent
                        ? feeTypeParentOptions(parameters, editingParameter?.id)
                        : caseFileTypeParentOptions(parameters, editingParameter?.id)}
                    />
                  ) : (
                    <Input
                      inputMode={numericParent ? "numeric" : undefined}
                      onInput={
                        numericParent ? cleanCompanyDigitsInputEvent : undefined
                      }
                    />
                  )}
                </Form.Item>
              );
            })}
            <Form.Item
              label="排序号"
              name="sort_order"
              rules={[{ required: true }]}
            >
              <InputNumber min={0} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="是否可用"
              name="is_active"
              valuePropName="checked"
            >
              <Switch checkedChildren="是" unCheckedChildren="否" />
            </Form.Item>
          </div>
          )}
        </Form>
      </Modal>

      <Modal
        open={Boolean(relationEditor)}
        title={
          relationEditor
            ? `${relationEditor.source.name}：${relationEditor.title}`
            : "关联维护"
        }
        okText="保存"
        cancelText="取消"
        confirmLoading={relationSaving}
        onOk={() => onSaveParameterRelation()}
        onCancel={() => {
          if (relationSaving) return;
          onRelationEditorClose();
        }}
        destroyOnHidden
      >
        {relationEditor && (
          <Form layout="vertical">
            <Form.Item label={relationEditor.targetLabel} required>
              <Select
                mode="multiple"
                placeholder={`请选择${relationEditor.targetLabel}`}
                options={relationTargetOptions}
                value={selectedRelationTargetIds}
                onChange={(value) => onSelectedRelationTargetIdsChange(value)}
                optionFilterProp="label"
              />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </>
  );
}
