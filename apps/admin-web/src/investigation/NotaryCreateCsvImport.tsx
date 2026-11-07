import { useState } from "react";
import { Alert, Button, Space, message } from "antd";
import { DownloadOutlined, UploadOutlined } from "@ant-design/icons";
import Table from "../components/ResizableTable";
import { api } from "../api";

// 原“公证信息导入”子菜单的“用 CSV 新建公证记录”。范文玲 11-06 说“别去掉 CSV”，菜单并成一个“公证书号仓库信息导入”后，
// 放在那个页面下面一块（501692/501694）；导入规则和接口不变。
const COLUMNS = ["来源线索编号", "公证标题", "负责人", "审核截止日", "公证书编号", "签发日期", "存放位置", "实物已收", "说明"];

type ImportResult = { created: number; failed: number; errors: { row: number; error: string }[]; created_ids?: number[] };

export function NotaryCreateCsvImport({
  personName,
  onImported,
}: {
  personName: (displayName: unknown, username: unknown) => string;
  onImported: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [uploading, setUploading] = useState(false);
  const downloadTemplate = async () => {
    try {
      const res = await api.get("/investigations/notaries/import-template", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "公证导入模板.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("模板下载失败");
    }
  };
  const upload = async () => {
    if (!file) {
      message.warning("请选择上传文件");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    setUploading(true);
    try {
      const { data } = await api.post<ImportResult>("/investigations/notaries/import", form);
      setResult(data);
      const created = await Promise.all((data.created_ids || []).map((id) => api.get(`/records/${id}`).then((res) => res.data)));
      setRows(created.map((row: any) => ({
        id: row.id,
        来源线索编号: row.data.clue_no,
        公证标题: row.title,
        负责人: personName(row.owner_display_name, row.owner),
        审核截止日: row.data.review_due_date,
        公证书编号: row.data.certificate_no,
        签发日期: row.data.certificate_issued_date,
        存放位置: row.data.certificate_storage_location,
        实物已收: row.data.physical_received ? "是" : "否",
        说明: row.description,
      })));
      message.success(`成功导入 ${data.created} 条公证记录`);
      setFile(null);
      onImported();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "导入失败");
    } finally {
      setUploading(false);
    }
  };
  return (
    <div className="notary-import-page notary-create-csv">
      <div className="notary-file-rule">用 CSV 新建公证记录：仅支持 UTF-8 CSV；来源线索必须已完成取证，且尚未生成公证记录。</div>
      <Space wrap>
        <Button icon={<DownloadOutlined />} onClick={downloadTemplate}>下载导入模板</Button>
        <label className="notary-upload-button">
          <UploadOutlined /> 选择文件
          <input
            hidden
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] || null);
              setResult(null);
              setRows([]);
              e.target.value = "";
            }}
          />
        </label>
        {file && <span className="notary-selected-file">{file.name}</span>}
        <Button type="primary" loading={uploading} onClick={upload}>上传文件</Button>
      </Space>
      {result && (
        <Alert
          style={{ marginTop: 12 }}
          type={result.failed ? "warning" : "success"}
          showIcon
          title={`成功 ${result.created} 条，失败 ${result.failed} 条`}
          description={result.errors?.slice(0, 8).map((x) => <div key={`${x.row}-${x.error}`}>第 {x.row} 行：{x.error}</div>)}
        />
      )}
      <Table
        size="small"
        rowKey={(row: any) => String(row.id ?? JSON.stringify(row))}
        dataSource={rows}
        locale={{ emptyText: "暂无待导入数据" }}
        columns={COLUMNS.map((title) => ({ title, dataIndex: title }))}
        scroll={{ x: 1200 }}
        pagination={false}
      />
    </div>
  );
}
