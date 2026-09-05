import {
Alert,
Button,
Card,
DatePicker,
Descriptions,
Form,
Input,
InputNumber,
Modal,
Select,
Space,
Table
} from "antd";
import { IPR_LAWSUIT_FEE_OPTIONS } from "../constants";
import type {
IprLawsuitCourt,
IprLawsuitFee,
IprLawsuitParty,
IprRecord,
} from "../types";

interface IprLawsuitPanelProps {
  detail: IprRecord;
  lawsuitCourts: IprLawsuitCourt[];
  lawsuitParties: IprLawsuitParty[];
  lawsuitFees: IprLawsuitFee[];
  courtInfoOpen: boolean;
  lawsuitCourtOpen: boolean;
  lawsuitPartyOpen: boolean;
  lawsuitFeeOpen: boolean;
  editingLawsuitCourt: IprLawsuitCourt | null;
  editingLawsuitParty: IprLawsuitParty | null;
  courtInfoForm: any;
  lawsuitCourtForm: any;
  lawsuitPartyForm: any;
  lawsuitFeeForm: any;
  onLoadManagement: () => void;
  onSaveCourtInfo: () => void;
  onCloseCourtInfo: () => void;
  onSaveLawsuitCourt: () => void;
  onCloseLawsuitCourt: () => void;
  onSaveLawsuitParty: () => void;
  onCloseLawsuitParty: () => void;
  onCreateLawsuitFee: () => void;
  onCloseLawsuitFee: () => void;
  onDeleteLawsuitCourt: (row: IprLawsuitCourt) => void;
  onDeleteLawsuitParty: (row: IprLawsuitParty) => void;
  onOpenEditCourt: (row: IprLawsuitCourt) => void;
  onOpenEditParty: (row: IprLawsuitParty) => void;
  onOpenAddCourt: () => void;
  onOpenAddParty: () => void;
  onOpenAddFee: () => void;
  onOpenCourtInfo: () => void;
}

export function IprLawsuitPanel({
  detail,
  lawsuitCourts,
  lawsuitParties,
  lawsuitFees,
  courtInfoOpen,
  lawsuitCourtOpen,
  lawsuitPartyOpen,
  lawsuitFeeOpen,
  editingLawsuitCourt,
  editingLawsuitParty,
  courtInfoForm,
  lawsuitCourtForm,
  lawsuitPartyForm,
  lawsuitFeeForm,
  onLoadManagement,
  onSaveCourtInfo,
  onCloseCourtInfo,
  onSaveLawsuitCourt,
  onCloseLawsuitCourt,
  onSaveLawsuitParty,
  onCloseLawsuitParty,
  onCreateLawsuitFee,
  onCloseLawsuitFee,
  onDeleteLawsuitCourt,
  onDeleteLawsuitParty,
  onOpenEditCourt,
  onOpenEditParty,
  onOpenAddCourt,
  onOpenAddParty,
  onOpenAddFee,
  onOpenCourtInfo,
}: IprLawsuitPanelProps) {
  return (
    <>
      <Alert
        type="info"
        showIcon
        message={'诉讼案件文件在“文档信息”页签中统一管理，可上传、下载及标记转文。'}
        style={{ marginBottom: 16 }}
      />
      <Card
        size="small"
        title="诉讼基本信息"
        extra={
          <Button size="small" onClick={onOpenCourtInfo}>
            维护诉讼信息
          </Button>
        }
      >
        <Descriptions
          size="small"
          column={2}
          items={[
            {
              key: "caseNo",
              label: "法院案号",
              children: detail.data.court_case_no || "—",
            },
            {
              key: "court",
              label: "受理法院",
              children: detail.data.court_name || "—",
            },
            {
              key: "judge",
              label: "承办法官",
              children: detail.data.judge || "—",
            },
            {
              key: "clerk",
              label: "书记员",
              children: detail.data.clerk || "—",
            },
            {
              key: "plaintiff",
              label: "原告",
              children: detail.data.plaintiff || "—",
            },
            {
              key: "defendant",
              label: "被告",
              children: detail.data.defendant || "—",
            },
            {
              key: "third",
              label: "第三人",
              children: detail.data.third_parties || "—",
              span: 2,
            },
          ]}
        />
      </Card>
      <Card
        size="small"
        title="诉讼法院信息"
        style={{ marginTop: 16 }}
        extra={
          <Space>
            <Button size="small" onClick={onLoadManagement}>
              刷新
            </Button>
            {detail.status === "在办" ? (
              <Button size="small" type="primary" onClick={onOpenAddCourt}>
                新增法院
              </Button>
            ) : null}
          </Space>
        }
      >
        <Table<IprLawsuitCourt>
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={lawsuitCourts}
          scroll={{ x: 780 }}
          columns={[
            { title: "审级", dataIndex: "court_level", width: 80 },
            { title: "法院", dataIndex: "court_name", width: 180 },
            {
              title: "案号",
              dataIndex: "case_no",
              width: 160,
              render: (value) => value || "—",
            },
            {
              title: "法官 / 书记员",
              width: 150,
              render: (_, row) =>
                [row.judge, row.clerk].filter(Boolean).join(" / ") || "—",
            },
            {
              title: "开庭日期",
              dataIndex: "hearing_date",
              width: 110,
              render: (value) => value || "—",
            },
            {
              title: "操作",
              fixed: "right",
              width: 140,
              render: (_, row) =>
                detail.status === "在办" ? (
                  <Space size={0}>
                    <Button type="link" onClick={() => onOpenEditCourt(row)}>
                      编辑
                    </Button>
                    <Button
                      type="link"
                      danger
                      onClick={() => onDeleteLawsuitCourt(row)}
                    >
                      删除
                    </Button>
                  </Space>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      </Card>
      <Card
        size="small"
        title="诉讼当事人"
        style={{ marginTop: 16 }}
        extra={
          detail.status === "在办" ? (
            <Button size="small" type="primary" onClick={onOpenAddParty}>
              新增当事人
            </Button>
          ) : null
        }
      >
        <Table<IprLawsuitParty>
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={lawsuitParties}
          columns={[
            { title: "身份", dataIndex: "party_type", width: 90 },
            { title: "名称", dataIndex: "name", width: 190 },
            {
              title: "联系人",
              dataIndex: "contact_name",
              width: 110,
              render: (value) => value || "—",
            },
            {
              title: "联系电话",
              dataIndex: "contact_phone",
              width: 135,
              render: (value) => value || "—",
            },
            {
              title: "地址",
              dataIndex: "address",
              ellipsis: true,
              render: (value) => value || "—",
            },
            {
              title: "操作",
              width: 140,
              render: (_, row) =>
                detail.status === "在办" ? (
                  <Space size={0}>
                    <Button type="link" onClick={() => onOpenEditParty(row)}>
                      编辑
                    </Button>
                    <Button
                      type="link"
                      danger
                      onClick={() => onDeleteLawsuitParty(row)}
                    >
                      删除
                    </Button>
                  </Space>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      </Card>
      <Card
        size="small"
        title="诉讼费用管理"
        style={{ marginTop: 16 }}
        extra={
          detail.status === "在办" ? (
            <Button size="small" type="primary" onClick={onOpenAddFee}>
              登记诉讼费用
            </Button>
          ) : null
        }
      >
        <Table<IprLawsuitFee>
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={lawsuitFees}
          columns={[
            {
              title: "费用类型",
              width: 160,
              render: (_, row) => row.title || row.fee_type || "—",
            },
            {
              title: "金额",
              dataIndex: "amount",
              width: 120,
              render: (value) =>
                value == null ? "—" : Number(value).toFixed(2),
            },
            {
              title: "费用日期",
              dataIndex: "fee_date",
              width: 120,
              render: (value) => value || "—",
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 100,
              render: (value) => value || "—",
            },
            {
              title: "备注",
              dataIndex: "remark",
              ellipsis: true,
              render: (value) => value || "—",
            },
          ]}
        />
      </Card>

      <Modal
        open={courtInfoOpen}
        title="维护诉讼基本信息"
        onCancel={onCloseCourtInfo}
        onOk={onSaveCourtInfo}
        okText="保存"
      >
        <Form form={courtInfoForm} layout="vertical">
          <div className="form-grid">
            <Form.Item name="court_case_no" label="法院案号">
              <Input />
            </Form.Item>
            <Form.Item name="court_name" label="受理法院">
              <Input />
            </Form.Item>
            <Form.Item name="judge" label="承办法官">
              <Input />
            </Form.Item>
            <Form.Item name="clerk" label="书记员">
              <Input />
            </Form.Item>
            <Form.Item name="plaintiff" label="原告">
              <Input />
            </Form.Item>
            <Form.Item name="defendant" label="被告">
              <Input />
            </Form.Item>
          </div>
          <Form.Item name="third_parties" label="第三人">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={lawsuitCourtOpen}
        title={
          editingLawsuitCourt ? "编辑诉讼法院" : "新增诉讼法院"
        }
        onCancel={onCloseLawsuitCourt}
        onOk={onSaveLawsuitCourt}
        okText="保存"
      >
        <Form form={lawsuitCourtForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              name="court_level"
              label="审级"
              rules={[{ required: true }]}
            >
              <Select
                options={["一审", "二审", "执行", "再审"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="court_name"
              label="法院名称"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item name="case_no" label="本审案号">
              <Input />
            </Form.Item>
            <Form.Item name="courtroom" label="法庭">
              <Input />
            </Form.Item>
            <Form.Item name="judge" label="承办法官">
              <Input />
            </Form.Item>
            <Form.Item name="clerk" label="书记员">
              <Input />
            </Form.Item>
            <Form.Item name="filing_date" label="立案日期">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="hearing_date" label="开庭日期">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={lawsuitPartyOpen}
        title={
          editingLawsuitParty ? "编辑诉讼当事人" : "新增诉讼当事人"
        }
        onCancel={onCloseLawsuitParty}
        onOk={onSaveLawsuitParty}
        okText="保存"
      >
        <Form form={lawsuitPartyForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              name="party_type"
              label="当事人身份"
              rules={[{ required: true }]}
            >
              <Select
                options={["原告", "被告", "第三人"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="name"
              label="名称"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item name="contact_name" label="联系人">
              <Input />
            </Form.Item>
            <Form.Item name="contact_phone" label="联系电话">
              <Input />
            </Form.Item>
          </div>
          <Form.Item name="address" label="地址">
            <Input />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={lawsuitFeeOpen}
        title="登记诉讼费用"
        onCancel={onCloseLawsuitFee}
        onOk={onCreateLawsuitFee}
        okText="登记"
      >
        <Form form={lawsuitFeeForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              name="lawsuit_fee_kind"
              label="费用类型"
              rules={[{ required: true }]}
            >
              <Select
                options={IPR_LAWSUIT_FEE_OPTIONS.map(({ value, label }) => ({
                  value,
                  label,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="amount"
              label="金额"
              rules={[{ required: true }]}
            >
              <InputNumber
                min={0.01}
                precision={2}
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item
              name="fee_date"
              label="费用日期"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="remark" label="备注">
              <Input />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </>
  );
}
