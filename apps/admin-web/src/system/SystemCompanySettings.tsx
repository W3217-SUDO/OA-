import {
  Alert,
  Button,
  Card,
  Form,
  Input,
} from "antd";
import {
  sanitizeCompanyDigitsInput,
  cleanCompanyDigitsInputEvent,
} from "./constants";

interface SystemCompanySettingsProps {
  companyForm: ReturnType<typeof Form.useForm>[0];
  onSaveCompany: () => void;
}

export function SystemCompanySettings({
  companyForm,
  onSaveCompany,
}: SystemCompanySettingsProps) {
  const fields: {
    name: string;
    label: string;
    normalize?: typeof sanitizeCompanyDigitsInput;
    type?: "email";
  }[] = [
    { name: "name", label: "公司名称" },
    { name: "code", label: "公司代码" },
    { name: "short_code", label: "公司字母短写代码" },
    { name: "address", label: "公司地址" },
    { name: "phone", label: "联系电话" },
    { name: "fax", label: "联系传真" },
    { name: "email", label: "联系邮箱", type: "email" },
    {
      name: "postal_code",
      label: "联系邮编",
      normalize: sanitizeCompanyDigitsInput,
    },
    { name: "bank_name", label: "开户银行" },
    {
      name: "bank_account",
      label: "开户帐号",
      normalize: sanitizeCompanyDigitsInput,
    },
    { name: "bank_address", label: "开户银行地址" },
  ];

  return (
    <Card className="panel system-focused" title="公司设置">
      <Alert
        type="info"
        message="请完善以下信息,方便我们更好的为您服务"
        style={{ marginBottom: 16 }}
      />
      <Form
        form={companyForm}
        className="system-config-form"
        labelCol={{ flex: "150px" }}
        wrapperCol={{ flex: "420px" }}
      >
        {fields.map(({ name, label, normalize, type }) => (
          <Form.Item
            key={name}
            name={name}
            label={label}
            normalize={normalize}
            rules={[
              { required: true, message: "请输入红星*必填项." },
              ...(type === "email"
                ? [{ type, message: "请填写正确联系邮箱！" }]
                : []),
            ]}
          >
            <Input
              type={type}
              inputMode={normalize ? "numeric" : undefined}
              onInput={normalize ? cleanCompanyDigitsInputEvent : undefined}
            />
          </Form.Item>
        ))}
        <Form.Item label=" ">
          <Button
            type="primary"
            onClick={onSaveCompany}
          >
            保存
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
