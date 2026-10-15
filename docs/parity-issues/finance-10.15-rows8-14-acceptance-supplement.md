# 10.15 第8至14行验收补充（1.1.439）

- 生产版本：`1.1.439`
- 代码提交：`ad90023e79e1ec6d54fccb185daa753b93a9260a`；版本提交：`dc4d14d7f234d1257c53438c53c8d9f4d30533a1`
- current：`/opt/sunhold-oa/runtime/enterprise/packages/1.1.439`；API/Web active；`https://huzhilawfirm.com/health` 返回 `{"status":"ok"}`。

## 真实 CODEX 闭环

1. 创建唯一内部费用 `CODEX-10.15-INTERNAL-EXPORT-20261016`，提交、审核、打包为 `P261016-29294816`。
2. 调用 `print-word?scope=internal_fee` 下载 DOCX；LibreOffice 回读证明内容包含：
   - `上海沪知律师事务所 提成付款申请单`
   - 付款包号、CODEX 请款号、CODEX 案号、金额 `1.23`、收款单位和备注。
3. 回滚/撤销付款包并删除内部费用，业务记录、付款包和请款号回查均为零残留。
4. `finance-fee-query.xls` 已由 CODEX 普通请款生成，LibreOffice 回读包含案号、客户、检索费、金额和付款状态。

## 导出接口回读

- 发票导出由原先的 500（错误导入 `_case_fee_display_type`）修复为明确的 409 业务校验：`发票 ... 的费用来源未映射完整或无权导出`；不再抛出服务器异常。
- 退费导出由原先的大集合参数 500 修复为分批读取，生产回读 `200`，文件大小 `259248` 字节。
- 案件费用开票状态导出生产回读 `200`，文件大小 `6020` 字节。
- 修复使用 `query_batches._scalars_in_batches`，避免 PostgreSQL `asyncpg` 参数上限；前端生产构建、Python 编译、运行包验包均通过。

## 浏览器证据

当前已登录标签在 `finance-payment-mine` 完成 CODEX 请款列表、详情、复制按钮、回滚成功、创建待提交状态和付款单打印页验收；打印页显示“上海沪知律师事务所”及真实金额/案号/合同号。

## 仍需补齐

- 平台财务中心全部导出入口的逐入口矩阵和文件回读。
- 删除权限矩阵需使用三类角色和终态数据分别完成接口验收。
- I8–I14 继续保持空白，直到上述两项完成；健康检查和单一导出证据不替代全范围验收。
