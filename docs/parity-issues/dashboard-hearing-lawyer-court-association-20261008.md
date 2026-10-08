# 控制台开庭排期显示实际法院和律师

## 基本信息

- **发现日期**：2026-10-08
- **状态**：已部署，待用户验收
- **页面位置**：控制台 -> 开庭排期
- **前端位置**：`apps/admin-web/src/Dashboard.tsx` 的 `hearingCols`，案件人员单元格由 `DashboardPersonCell` 展示
- **后端位置**：`GET /api/dashboard?section=cases` -> `apps/api-server/app/core/dashboard_cases.py`
- **截图证据**：`codex-clipboard-f33485dc-2b75-498e-9f8e-a9f02001288b.png`
- **用户原始要求**：这个要写入实际的律师，跟法院啊，关联好的

## 问题现象

控制台开庭排期的“开庭法院”显示 `京0108`、`赣0404` 等法院编码，“开庭律师”显示 `shenjf` 等登录账号，不符合实际业务页面应显示的法院名称和律师姓名。截图中的“经办律师”和“律师助理”已经是中文姓名，显示不一致。

## 数据与关联核对

- 线上案件 `HZMS2600090` 的排期数据为法院编码 `赣0404`、开庭律师账号 `shenjf`。
- 法院主数据 `SystemParameter(category="court", code="赣0404")` 对应“九江市濂溪区人民法院”。
- 人员主数据 `User(username="shenjf")` 对应“沈建锋”。
- 案件原始关联字段保持账号/编码存储，不能通过写死名称或修改历史案件数据解决。

## 根因

案件排期投影 `_dashboard_case_hearing` 和 `HearingSchedule` 分支直接把 `court`、`hearing_lawyer` 放入控制台响应。该响应没有查询法院主数据，也没有复用已有的人员显示名解析逻辑 `_dashboard_people`，前端只能原样显示编码和登录账号。

## 整改规则

1. 法院按 `SystemParameter.category="court"` 的 `code -> name` 真实关联显示。
2. 律师按案件排期保存的账号与 `User.username -> User.display_name` 真实关联显示。
3. 经办律师、律师助理沿用同一人员解析规则，已经保存中文姓名的历史数据继续保留。
4. 不写死法院名称、不把显示名称回写覆盖案件原始关联、不用假数据或静默成功兜底。

## 修改与验证记录

- **修改文件**：`apps/api-server/app/core/dashboard_cases.py`；本问题记录文档
- **定向验证**：已核对线上案件 `HZMS2600090` 的 `赣0404 -> 九江市濂溪区人民法院`、`shenjf -> 沈建锋` 主数据关联；响应投影同时覆盖案件排期和 `HearingSchedule` 数据分支
- **构建/检查**：Python 编译通过；前端生产构建通过（5942 modules）；菜单覆盖审计通过（295 nodes / 248 leaves / 0 uncovered）；`git diff --check` 通过；运行包校验通过
- **Git 提交与部署**：发布提交 `01c0b51424b6260da2d0fdf677383a0f07a2cff2`，标签 `v1.1.258`；已推送 GitHub `dev`；部署版本 `1.1.258`
- **服务检查**：`sunhold-dev-api`、`sunhold-dev-web` 均为 active，API `/health` 返回 `{"status":"ok"}`，公网页面 HTTP 200
- **线上页面验收**：待用户刷新控制台确认

## 后续状态

- **当前状态**：已部署，待用户验收
- **整改情况**：已完成真实法院和律师主数据关联显示。法院仍按编码存储，页面按启用法院参数解析名称；律师仍按账号存储，页面按员工账号解析姓名；未回写或修改历史案件数据。浏览器最终验收需用户刷新 `控制台 -> 开庭排期`，确认“开庭法院”为法院全称、“开庭律师”为实际姓名。
