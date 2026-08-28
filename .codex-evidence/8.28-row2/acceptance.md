# 8.28 第2行本地验收

## 变更

- 案件详情不再无条件显示空白“法院信息”和“归档信息”。
- 一审、二审、执行三组法院字段分别按有效数据出现，互不连带。
- 归档字段存在或案件处于归档流程状态时才显示归档区域。
- `-`、`—`、空字符串、`null` 等占位值按无数据处理。

## 自动化验证

- `node --test --experimental-strip-types caseDetailSectionVisibility.test.mjs`：3/3 通过。
- `npm.cmd run build`：通过，Vite 5637 modules transformed；仅有既有 chunk size warning。

## Codex 内置浏览器

隔离环境：Web `http://127.0.0.1:5301`，API `http://127.0.0.1:8098`，独立 SQLite 数据库。

- `CODEX828R2EMPTY`：详情已加载，`法院信息=0`、`归档信息=0`。
- `CODEX828R2FIRST`：仅显示一审法院和一审案号；二审、执行、归档均未出现。
- `CODEX828R2SECOND`：仅显示二审法院和二审案号；一审、执行、归档均未出现。
- `CODEX828R2ARCHIVE`：法院信息未出现；归档信息显示正常归档、提交时间、审核状态和归档号。
- 浏览器日志无 API/运行时失败；存在的日志仅为项目基线 Ant Design 弃用警告。

截图：

- `C:/Users/Administrator/Desktop/OA系统/问题/_返工验收/8.28_第2行/local-empty-hidden.png`
- `C:/Users/Administrator/Desktop/OA系统/问题/_返工验收/8.28_第2行/local-first.png`
- `C:/Users/Administrator/Desktop/OA系统/问题/_返工验收/8.28_第2行/local-second.png`
- `C:/Users/Administrator/Desktop/OA系统/问题/_返工验收/8.28_第2行/local-archive.png`

本地测试数据前缀：`CODEX828R2*`。验收结束后隔离数据库、上传目录和临时服务均删除，不影响共享或线上数据。
