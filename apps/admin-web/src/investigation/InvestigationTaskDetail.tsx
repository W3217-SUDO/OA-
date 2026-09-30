import { useEffect, useRef, useState } from "react";
import { Alert, Button, Collapse, Descriptions, Modal, Space, Spin } from "antd";
import Table from "../components/ResizableTable";
import dayjs from "dayjs";
import { api } from "../api";
import { AttachmentPreviewContent, type PreviewAttachment } from "../components/common/AttachmentContent";
import type { Attachment, Row } from "./types";
import "./investigation-task-detail.css";

interface DetailResponse {
  record: Row;
  parent: Row;
  materials: Attachment[];
  items: Row[];
  total: number;
}
interface Props {
  record: Row;
  personName: (display: unknown, username: unknown) => string;
  onOpenCustomer: (name: string) => void;
  onOpenClue: (serial: string, module: "clue") => void;
}
const dateText = (value: unknown) => value && dayjs(String(value)).isValid() ? dayjs(String(value)).format("YYYY-MM-DD") : "—";
const region = (row: Row) => row.data.region || [row.data.province, row.data.city, row.data.district].filter(Boolean).join(" ") || "—";
const errorText = (error: any, message: string) => typeof error?.response?.data?.detail === "string" ? error.response.data.detail : error?.message || message;

export default function InvestigationTaskDetail({ record, personName, onOpenCustomer, onOpenClue }: Props) {
  const [recordId, setRecordId] = useState(record.id);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [revision, setRevision] = useState(0);
  const [detail, setDetail] = useState<DetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fileError, setFileError] = useState("");
  const [preview, setPreview] = useState<PreviewAttachment | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const fileRequest = useRef<AbortController | null>(null);
  const previewUrl = useRef<string | null>(null);
  const closePreview = () => {
    fileRequest.current?.abort();
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null;
    setPreview(null);
    setFileLoading(false);
  };
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setDetail(null);
    api.get(`/investigations/${recordId}/task-detail`, { params: { page, page_size: pageSize }, signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setDetail(data); })
      .catch((failure) => { if (!controller.signal.aborted) setError(errorText(failure, "调查详情加载失败")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [recordId, page, pageSize, revision]);
  useEffect(() => () => {
    fileRequest.current?.abort();
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
  }, []);
  const openRecord = (id: number) => { closePreview(); setFileError(""); setRecordId(id); setPage(1); };
  const openFile = async (file: Attachment, download = false) => {
    closePreview();
    const controller = new AbortController();
    fileRequest.current = controller;
    setFileError("");
    setFileLoading(true);
    try {
      const metadata = download ? null : (await api.get(`/attachments/${file.id}/preview`, { signal: controller.signal })).data;
      if (metadata?.kind === "unsupported") throw new Error(metadata.detail || "当前文件无法在线查看，请下载原文件");
      if (metadata?.kind === "text") {
        if (!controller.signal.aborted) setPreview({ name: file.original_name, kind: "text", text: metadata.text });
        return;
      }
      const response = await api.get(`/attachments/${file.id}/download`, { responseType: "blob", signal: controller.signal });
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(response.data);
      if (download) {
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = file.original_name;
        anchor.click();
        URL.revokeObjectURL(url);
      } else {
        previewUrl.current = url;
        setPreview({ name: file.original_name, kind: metadata.kind === "workbook" ? "xlsx" : metadata.kind, blob: response.data, url, text: metadata.text });
      }
    } catch (failure: any) {
      if (!controller.signal.aborted) {
        let message = errorText(failure, "调查资料读取失败");
        if (failure?.response?.data instanceof Blob) {
          try { message = JSON.parse(await failure.response.data.text()).detail || message; } catch { /* 非 JSON 错误保留请求错误。 */ }
        }
        if (!controller.signal.aborted) setFileError(message);
      }
    } finally {
      if (!controller.signal.aborted) setFileLoading(false);
    }
  };
  const source = detail?.record;
  const parent = detail?.parent;
  const isChild = source?.module === "task";
  const basic = parent && <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }} items={[
    { key: "number", label: "调查编号", children: parent.serial_no },
    { key: "source", label: "案源人", children: personName(parent.data.source_owner_display_name, parent.data.source_owner || parent.data.publisher) },
    { key: "right", label: "权利类型", children: parent.data.right_type || "—" },
    { key: "customer", label: "权利人", children: parent.customer ? <Button type="link" onClick={() => onOpenCustomer(parent.customer)}>{parent.customer}</Button> : "—" },
    { key: "begin", label: "授权开始时间", children: dateText(parent.data.authorized_from) },
    { key: "end", label: "授权结束时间", children: dateText(parent.data.authorized_to) },
    { key: "region", label: "调查区域", children: region(parent), span: 2 },
    { key: "title", label: "调查事项", children: parent.title, span: 2 },
    { key: "remark", label: "备注", children: parent.description || "—", span: 2 },
  ]} />;
  const materials = <Table<Attachment> size="small" rowKey="id" dataSource={detail?.materials || []} pagination={{ pageSize: 10, showSizeChanger: true }} scroll={{ x: 650 }} columns={[
    { title: "上传人", width: 100, render: (_, file) => personName(file.uploader_display_name, file.uploader) },
    { title: "文件名称", dataIndex: "original_name" },
    { title: "资料类别", dataIndex: "category", width: 120 },
    { title: "文档日期", width: 120, render: (_, file) => dateText((file as Attachment & { document_date?: string }).document_date || file.created_at) },
    { title: "操作", width: 120, render: (_, file) => <Space size={0}><Button type="link" disabled={fileLoading} onClick={() => void openFile(file)}>查看</Button><Button type="link" disabled={fileLoading} onClick={() => void openFile(file, true)}>下载</Button></Space> },
  ]} locale={{ emptyText: "暂无调查资料" }} />;
  const related = <Table<Row> size="small" rowKey="id" dataSource={detail?.items || []} scroll={{ x: 720 }} pagination={{ current: page, pageSize, total: detail?.total || 0, showSizeChanger: true, onChange: (next, size) => { setPage(next); setPageSize(size); } }} columns={isChild ? [
    { title: "线索编号", dataIndex: "serial_no", width: 175, render: (value) => <Button type="link" onClick={() => onOpenClue(value, "clue")}>{value}</Button> },
    { title: "调查时间", width: 115, render: (_, row) => dateText(row.data.collected_at) },
    { title: "侵权方式", width: 110, render: (_, row) => row.data.infringement_method || row.data.platform || "—" },
    { title: "店铺名称", render: (_, row) => row.data.shop_name || row.title || "—" },
    { title: "调查地址", render: (_, row) => row.data.address || region(row) },
    { title: "状态", dataIndex: "status", width: 100 },
  ] : [
    { title: "子任务编号", dataIndex: "serial_no", width: 175, render: (value, row) => <Button type="link" onClick={() => openRecord(row.id)}>{value}</Button> },
    { title: "调查员", width: 110, render: (_, row) => personName(row.owner_display_name, row.owner) },
    { title: "调查区域", render: (_, row) => region(row) },
    { title: "开始时间", width: 120, render: (_, row) => dateText(row.data.start_date || row.data.started_at || row.data.authorized_from) },
    { title: "结束时间", width: 120, render: (_, row) => dateText(row.data.end_date || row.data.ended_at || row.data.deadline || row.data.authorized_to) },
  ]} locale={{ emptyText: isChild ? "暂无调查线索" : "暂无调查子任务" }} />;
  return <div className="investigation-task-detail">
    <Space style={{ marginBottom: 12 }}><Button onClick={() => setRevision((value) => value + 1)}>刷新</Button>{recordId !== record.id && <Button onClick={() => openRecord(record.id)}>返回调查任务</Button>}</Space>
    {error && <Alert type="error" showIcon message={error} />}
    {fileError && <Alert type="error" showIcon message={fileError} style={{ marginBottom: 12 }} />}
    <Spin spinning={loading}>
      {detail && <Collapse defaultActiveKey={isChild ? ["task", "basic", "materials"] : ["basic", "materials", "children"]} items={[
        ...(isChild && source ? [{ key: "task", label: `任务信息：${source.serial_no}`, children: <>
          <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }} items={[
            { key: "owner", label: "调查员", children: personName(source.owner_display_name, source.owner) },
            { key: "region", label: "调查区域", children: region(source) },
            { key: "begin", label: "开始时间", children: dateText(source.data.start_date || source.data.started_at || source.data.authorized_from) },
            { key: "end", label: "结束时间", children: dateText(source.data.end_date || source.data.ended_at || source.data.deadline || source.data.authorized_to) },
            { key: "deadline", label: "任务截止日期", children: dateText(source.data.deadline) },
            { key: "remark", label: "任务说明", children: source.description || "—" },
          ]} /><h4>线索信息</h4>{related}
        </> }] : []),
        { key: "basic", label: "基本信息", children: basic },
        { key: "materials", label: "调查资料", children: materials },
        ...(!isChild ? [{ key: "children", label: "调查子任务", children: related }] : []),
      ]} />}
    </Spin>
    <Modal title={preview?.name || "调查资料"} open={Boolean(preview)} onCancel={closePreview} footer={<Button onClick={closePreview}>关闭</Button>} width={1000} destroyOnHidden>
      <AttachmentPreviewContent preview={preview} />
    </Modal>
  </div>;
}
