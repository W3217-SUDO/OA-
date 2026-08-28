# 8.28 第25行本地验收

- 问题：仓库一览表填写公证书号后提示“仓库数据加载失败”，无法查询案件证物库位。
- 根因：后端用 `filter(None, ...)` 处理 SQLAlchemy 条件，填写任一筛选项时会对 SQL 表达式执行布尔判断并返回500；公证书号仅查询 `notary_no`，未兼容迁移字段。
- 修复：逐项追加非空筛选条件；公证书号统一查询 `notary_no`、`notary_nos`、`certificate_no`、`notarization_no`；返回数据统一投影 `notary_no`，确保迁移证物能显示公证书号。

## 自动测试

- 后端专项及相邻案件公证库位回归：`python -m unittest warehouse_notary_search_row25_test.py case_notary_warehouse_location_contract_test.py`，4/4 通过。
- 后端编译：`python -m py_compile app/main.py warehouse_notary_search_row25_test.py`，通过。
- 生产构建：`npm.cmd run build`，通过；正式版本保持 1.1.27，5637 modules transformed。

## Codex 内置浏览器

- 本地仓库 `CODEX-828-R25-仓库` / 库位 `CODEX-828-R25-库位A` 创建迁移形态证物，原始数据仅保留 `certificate_no=CODEX-828-R25-3333`。
- 仓库一览表输入 `3333` 并查询：无“仓库数据加载失败”，仅返回目标证物1条。
- 结果正确显示公证书号 `CODEX-828-R25-3333` 与库位 `CODEX-828-R25-库位A`；编号9999的对照证物未混入。
- 证据：`browser-notary-search-location.png`。

## 清理

- 本地验收数据前缀：`CODEX-828-R25-`。
- 本行无数据库结构迁移或正式数据补丁。
