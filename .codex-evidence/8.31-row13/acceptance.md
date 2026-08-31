# 8.31 第13行验收记录

## 问题与口径

- 工作表：`8.31`，第13行。
- 问题：案件平台费用中的代理费与律所费用类型混用。
- 目标：操作入口仍为“新增代理费”；平台费用只能选择“平台代理费”，律所费用继续保留律师代理费、律师咨询费、律师培训费、律师见证费。

## 自动化验证

- 前端：`node --test casePlatformAgencyFeeRow13.test.mjs caseAgencyFeeTypesRow12.test.mjs`，5/5 通过。
- 后端：`python -m unittest case_platform_agency_fee_row13_test.py case_agency_fee_types_row12_test.py`，5/5 通过。
- 语法：`python -m py_compile app/main.py case_platform_agency_fee_row13_test.py` 通过。
- 生产构建：`npm.cmd run build` 通过，Vite 转换 5638 个模块；正式版本仍为 1.1.36，仅有既有 chunk-size 提示。

## 本地 Google Chrome 验收

- 隔离环境：前端 `http://127.0.0.1:5313`，API `http://127.0.0.1:8063`，隔离 SQLite `row13.db`。
- 案件：`CODEX-831-R13-CASE`，进入“平台费用”。
- 空状态显示“新增代理费”；点击后自动选中平台合同 `CODEX-831-R13-PLATFORM｜第13行平台合同`。
- 代理费类型下拉精确计数：`平台代理费` 1 项；`代理费` 0 项；`律师代理费` 0 项。
- 创建金额 `1313.13` 成功，列表显示合同、类型“平台代理费”、金额和提交人；刷新后仍为 1 条并保持一致。
- 数据库核对：`expense_scope=平台`、`expense_subtype=平台代理费`、`fee_type=代理费`、`contract_no=CODEX-831-R13-PLATFORM`、`amount=1313.13`。
- API 日志无 Traceback、ERROR 或 500。Chrome 控制台无业务异常，仅有项目既有的 Ant Design 弃用/上下文警告。
- 初次隔离夹具编码错误已在正式验收前修正，未计作产品失败。

## 证据

- `C:\Users\Administrator\Desktop\OA系统\问题\_返工验收\8.31_第13行\local\01-platform-agency-only-option.png`
- `C:\Users\Administrator\Desktop\OA系统\问题\_返工验收\8.31_第13行\local\02-platform-agency-refresh-persisted.png`

## 最终门禁

- 已重新核对原工作簿第13行完整文字、C/D 两张图片及锚点，整改口径与原系统目标一致。
- 本行未修改 Excel 完成标记、正式版本、tag、服务器或线上数据库。
