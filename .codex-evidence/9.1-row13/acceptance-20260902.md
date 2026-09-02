# 9.1 第13行本地整改验收（2026-09-02）

## 结论

“我发布的调查任务 → 我的调查任务/过期调查任务”现为发布人管理的父调查事项视图，数据按 publisher 归属，任务负责人是调查主管；列表只提供刷新、修改、上传调查资料，不提供调查员执行环节的新增线索或关闭任务并生成报告。

## 修改与根因

- 既有修复：`apps/admin-web/src/InvestigationCenterPage.tsx` 将两页统一到 `module=investigation + investigation_view=published`，按授权结束日形成过期子集，并限定动作集合。
- 契约测试：`apps/admin-web/investigationPublishedParentTaskRow13.test.mjs`；相关前端回归覆盖发布过滤、管理员可见性、菜单层级和页面契约。
- 根因：发布人父调查管理视图曾复用调查员子任务执行页，因而同时发生数据层级、角色关系和动作权限错位。
- 旧系统源码/数据、新系统源码/数据的完整追踪见 `reading-confirmation-20260902.md`。

## 测试

- `node investigationPublishedParentTaskRow13.test.mjs`：通过。
- `node --test investigationPublishedFilter.test.mjs investigationAdminPublishedVisibility.test.mjs investigationTaskMenuParity.test.mjs investigationCenterFrontendParity.test.mjs`：25/25 通过。
- `npm.cmd run build`：通过，5643 modules transformed；仅有既有 chunk size 警告。
- `git diff --check` 与 CodeGraph 同步在提交前通过。

## 独立 Chrome 验收

- 我的调查任务：同时显示有效和过期两条父调查，字段与旧系统一致；刷新/修改/上传各 1 个，新增线索和关闭报告均为 0：`local-publisher-mine.png`。
- 未选记录点击修改出现“请只勾选一条记录”，没有 records 写请求：`local-publisher-no-selection-blocked.png`。
- 选中父调查后，修改打开父调查表单且负责人锁定为调查主管：`local-publisher-edit-parent.png`。
- 上传调查资料打开父调查材料目录；无文件时被前端阻断，没有附件写请求：`local-publisher-upload-empty-blocked.png`。
- 过期页只显示授权到 2026-08-01 的过期记录，不显示有效记录；整页刷新后保持：`local-publisher-overdue.png`、`local-publisher-overdue-refreshed.png`。
- API 日志仅命中 `GET /api/v1/records?module=investigation&scope=mine&investigation_view=published`，records 写请求为 0。

## 持久化与清理

- 隔离 SQLite 保持两条父调查数据：publisher=`row13publisher`、owner=`row13supervisor`，授权结束日分别为 2027-09-01/2026-08-01；刷新前后无变化。
- 验收后关闭本行新旧 Chrome 标签，停止 8013/15313，删除本行 SQLite、账号、记录、日志、种子脚本、临时环境文件和 `node_modules` junction。
- 未部署、未改版本/tag/dev/线上数据库/8089/工作簿状态。

## 截图 SHA256

- `legacy-publisher-active-empty.png`: `D3E43EC8C74B670DD6F10A1E73BFABB8648EAED4B61332C4AF201D6399FDB799`
- `legacy-publisher-overdue-empty.png`: `D3E43EC8C74B670DD6F10A1E73BFABB8648EAED4B61332C4AF201D6399FDB799`
- `local-publisher-mine.png`: `5087FD00059823E824AA93A54EFB1B20FB529AED4E62DCC91DC6260D970012A8`
- `local-publisher-no-selection-blocked.png`: `016BEB3FB05AAB00AA440D53692E080ABC3066271199E2BCCDCED11BF930DB42`
- `local-publisher-upload-empty-blocked.png`: `500C3654E1C377B56A0695CCC2D31C9CCA7445E27B3A6E2497DCF34CC3AFD13D`
- `local-publisher-edit-parent.png`: `BECCB12A2D8F0698DF96C1849827960DFDF05FDD6F690D81E3B76C76A50C919B`
- `local-publisher-overdue.png`: `EA8E27DB7A2E022342296EC43D1FDA286DBF664A51D8F4C9B32D6048345B3251`
- `local-publisher-overdue-refreshed.png`: `88515EB982EC0A6DA27183AD9CD9FDA2375AC4F0CFD38207F0B5D8B7A2FE07C2`

## 冲突风险

`InvestigationCenterPage.tsx` 是第13、15行共享热点文件；集成时必须同时保留父调查 published 视图的按钮限制与第15行子任务门禁。当前 checkpoint 仅新增本轮证据/状态文档，没有再次改写共享实现。
