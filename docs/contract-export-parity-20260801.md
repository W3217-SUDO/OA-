# 合同列表导出对照证据

- 旧系统只读菜单顺序：合同中心 → 我的合同；旧页面显示“导出Excel”、合同查看、合同变更、合同用印、合同付款、合同开票、新建案件、新建调查任务、合同归档及 10/15/20/50/100/200 分页。
- 本地页面：`http://127.0.0.1:5173/?page=contract-mine`，热更新后实际显示“导出Excel”与原有“导出CSV”两个按钮，保留本地额外 CSV 能力；合同筛选字段与旧站一致。
- 浏览器已实际点击本地“导出Excel”按钮；当前浏览器下载事件未提供可读对象，但后端同一认证会话实测响应为 HTTP 200、`Content-Type: application/vnd.ms-excel`、`Content-Disposition: attachment; filename*=UTF-8''contract-2026-08-01.xls`，正文 764 字节，SpreadsheetML `Workbook` 非空可解析。
- 筛选证据：以合同名称 `test_合同` 作为查询条件调用 Excel 导出接口，返回体 764 字节；接口接收 `title/serial_no/type/customer/case_no/fee_type/contract_body/source_person/signed_at_start/signed_at_end` 并在导出前按当前权限范围过滤。
- 旧系统未执行新增、编辑、保存、审批、上传、下载或删除；本轮未创建测试业务数据。
