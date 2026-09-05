import {
  Button,
  Card,
  Form,
  Input,
} from "antd";
import {
  sanitizeShareDaysInput,
  cleanShareDaysInputEvent,
  isShareDaysValueValid,
} from "./constants";

interface SystemShareSettingsProps {
  shareForm: ReturnType<typeof Form.useForm>[0];
  onSaveShare: () => void;
}

export function SystemShareSettings({
  shareForm,
  onSaveShare,
}: SystemShareSettingsProps) {
  return (
    <Card className="panel system-focused" title="客户共享时间设置">
      <Form
        form={shareForm}
        className="share-config-form"
        labelCol={{ flex: "150px" }}
        wrapperCol={{ flex: "220px" }}
      >
        {[
          ["all_days", "全部客户"],
          ["filed_days", "立案客户"],
          ["premium_days", "高级客户"],
          ["standard_days", "中级客户"],
          ["basic_days", "初级客户"],
          ["shared_days", "共享客户"],
        ].map(([name, label]) => (
          <Form.Item
            key={name}
            name={name}
            label={label}
            normalize={sanitizeShareDaysInput}
            rules={[
              { required: true },
              {
                validator: (_rule, value) =>
                  isShareDaysValueValid(value)
                    ? Promise.resolve()
                    : Promise.reject(
                        new Error("请输入 1–3650 之间的天数"),
                      ),
              },
            ]}
          >
            <Input
              inputMode="numeric"
              maxLength={4}
              onInput={cleanShareDaysInputEvent}
              addonAfter="天"
            />
          </Form.Item>
        ))}
        <Form.Item label=" ">
          <Button
            type="primary"
            onClick={onSaveShare}
          >
            保存
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
