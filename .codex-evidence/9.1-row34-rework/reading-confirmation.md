# 9.1 第34行读取与闭环确认

- 权威工作簿：`C:\Users\Administrator\Desktop\OA系统\问题\OA系统对接9.1.xlsx`
- 工作表/行：`9.1` / `A34:I34`（工作表实际使用范围 `A1:I37`）
- 结构读取：公式模式与缓存值模式分别读取且值一致；本行无公式、批注、超链接、合并、隐藏列或隐藏行；行高 `55.5`。
- 完成门禁：F34 为红字返工并指出新问题，H34 的历史数字 `1` 已失效；未改写工作簿及其完成状态。

## 逐列确认

| 列 | 表头 | 完整文字/内容 | 格式/图片 | 读取用途 |
|---|---|---|---|---|
| A34 | 模块 | 案件中心 | 样式 16；无图 | 业务模块 |
| B34 | 问题 | 案件里，平台费用的代理费和律所费用是有区别的，平台费用里的代理费只有一种类型，就是平台代理费 | 样式 18；无图 | 原始需求，逐字保留 |
| C34 | 截图 | 空文本 | 样式 16；1 张新系统入口图 | 当前案件“平台费用 -> 新增案件费用 -> 新增代理费”入口 |
| D34 | 原系统 | 空文本 | 样式 16；1 张旧系统目标图 | 旧系统平台费用新增代理费及唯一类型 |
| E34 | 发起时间 | 空 | 样式 33；无图 | 无提交日期 |
| F34 | 测试 | 新建平台代理费时，选择费用类型，界面有问题，一是字体竖起来了，二是多一个 | 样式 24；字体色 `FFFE0300`；无图 | 最高优先级返工文字：选项逐字换行且出现额外类型 |
| G34 | 截图 | 空文本 | 样式 16；1 张返工截图 | 当前选择器同时出现“律师见证费”和“平台代理费”，窄列造成逐字竖排 |
| H34 | 完成状态 | 1 | 数字 | 已被 F34/G34 返工撤销 |
| I34 | 完成时间 | 空 | 样式 33；无图 | 无完成时间 |

## OOXML 图片锚点与逐图确认

| 证据文件 | OOXML 媒体 | 锚点 | 字节 | SHA256 | 视觉语义 |
|---|---|---|---:|---|---|
| `source/row34-col3-image402.png` | `xl/media/image402.png` | C34 | 116615 | `ef66bdcd612cdccb924dc64be7b110a0599e87a0f4de15dc413a9db943ea5d96` | 新系统案件详情“平台费用”选项卡展开“新增案件费用”，红框标出“新增代理费”入口 |
| `source/row34-col4-image403.png` | `xl/media/image403.png` | D34 | 166650 | `4e07b761431b5afe0e0483a2a3b6479905301208148927ad360afdabfc00b4c9` | 旧系统相同入口打开“新增费用”，费用类型仅“平台代理费” |
| `source/row34-col7-image404.png` | `xl/media/image404.png` | G34 | 130929 | `40d4ed26f27845c042a76bf39068bbf9316a40206fac57d5bb3a6c8d21904615` | 返工现场同时出现“律师见证费”“平台代理费”，下拉过窄导致中文逐字换行 |

三张源图均以原始分辨率逐张视觉复核；源图恢复后的字节数与 SHA256 和首次提取记录完全一致。

## VibeHub 与并列专业定位表达

- 脱敏候选：`下拉菜单`、`文本换行`、`选项约束`。
- Resolver：`下拉菜单`命中 [下拉菜单](https://vibe-hub.org/dropdown)；后两项无可靠结果，未虚构链接。
- 专业定位表达：这是**单选选择器（Select）的候选域约束与弹层排版回归**：平台代理费入口的选项集合应收敛为唯一合法值“平台代理费”，同时选择器弹层应具备足够宽度并禁止逐字断行，确保候选文本横向完整呈现。
- 上述表达与 B34/F34 原文并列使用，没有替换、缩减原始需求。

## 旧系统同入口、源码与数据

- 动态环境：`http://localhost:8091`，角色“管理者”。工作簿截图案件 `SHMS2300502` 不在本地旧库，未伪造该案；改用本地真实案件详情 `SHMS2600394`，沿同角色、同业务入口“案件详情 -> 平台费用 -> 新增代理费”复现。
- 动态 DOM：费用类型原生选择器只有占位项“请选择”和唯一业务项“平台代理费”；选择后文字正常横排。
- 旧源码：`Areas/Legal/Controllers/CaseFeeController.cs` 的 `TradFeeList`/`TradFeeCreate` 固定走平台费用分组；`Areas/Legal/Views/CaseFee/PartialView/TradFeeList.cshtml` 与 `TradFeeCreate.cshtml` 提供专用新增代理费入口；`Scripts/Legal/Case/Legal.Case.js` 在 `NonOfficeFee + GroupId.Trad` 分支只追加 `FeeTypeId == 11020050`。
- 旧数据：只读查询 `dbo.BAS_Case_FeeType` 证实代理费族同时含律师代理/咨询/培训/见证费及 `11020050 平台代理费`；平台入口的权威约束来自旧源码的 `11020050` 精确过滤，而非笼统代理费根节点。
- 浏览器证据：
  - `old-system/01-platform-agency-single-option.png`，127215 字节，SHA256 `2fa21ace1f209b1376ff9050ac74f5c138b97df7f7ea84c5576a9a6c34c94c0c`；同入口弹窗与 DOM 唯一选项证据。
  - `old-system/02-platform-agency-selected.png`，127186 字节，SHA256 `d870a2e649c75cc1cdbc3b5b32bd714dc102325ef999993cef9d538be11c9fa6`；选择后“平台代理费”横排展示。

## 新系统追踪、根因与修改

- 前端既有正确实现来自历史提交 `d9e4243`：`src/feeTypeHierarchy.mjs` 对“平台 + 代理费”只保留名称精确等于“平台代理费”的项并按名称去重；`CaseCenterPage.tsx` 为两个费用类型 `TreeSelect` 设置 `popupMatchSelectWidth={180}`；相关 CSS 扩宽费用类型列。未重复返工这些已经形成的代码。
- 新系统主数据实测故意加入两个同名“平台代理费”及“律师见证费”后，前端仍只显示一个横排的“平台代理费”，证明候选域过滤、去重和弹层排版有效。
- 失败路径暴露的后端根因：`apps/api-server/app/main.py::_resolve_case_fee_type_master` 的有主数据分支此前只检查代理费根节点推导出的宽泛 `expense_scopes`，没有调用既有 `_validate_finance_fee_scope_subtype`。因此绕过 UI 直接提交“平台 + 律师见证费”会被错误接受；无主数据兼容分支反而已有该校验，两个分支不一致。
- 修改：在有主数据分支返回前统一调用 `_validate_finance_fee_scope_subtype(scope, item.name, option["base_fee_type"])`，让单条新增、批量入口和兼容分支共享“平台代理费只能是平台代理费”的服务端边界。
- 回归：`case_platform_agency_fee_row13_test.py` 新增动态主数据测试，同时证明“平台 + 律师见证费”返回 422、“平台 + 平台代理费”仍返回 201。

## 聚焦测试与生产构建

- 前端：`node --test casePlatformAgencyFeeRow34.test.mjs casePlatformAgencyFeeRow13.test.mjs`，6/6 通过，覆盖唯一候选、律所费用隔离及横排宽度。
- API：`python -m unittest case_platform_agency_fee_row13_test.py`，5/5 通过，包含新增主数据失败/成功分支。
- 生产构建：`npm.cmd run build` 通过，3986 modules transformed；只有既有的大 chunk 警告，无构建失败。
- 补丁检查：`git diff --check` 通过。

## 独立 Chrome 验收、持久化与失败路径

- 隔离范围：前端 `15434`、API `18034`、SQLite `row34.sqlite`、数据前缀 `CODEX-901-R34-`、独立 Chrome 窗口与本证据目录；未操作其他任务端口、数据库、标签页或服务。
- 正常路径：管理者进入 `CODEX-901-R34-CASE` -> 平台费用 -> 新增代理费；选择器只出现一个横排“平台代理费”，无“律师见证费”、无同名重复；通过 UI 新增金额 `3400.34` 成功。
- 持久化：页面刷新并重新进入平台费用后，合同 `CODEX-901-R34-PLATFORM`、费用类型“平台代理费”、金额 `3400.34` 仍存在；SQLite 同时核对 `fee_type_id=33`、`fee_type_code=1102050`、`fee_type_path=代理费 / 平台代理费`、`expense_scope=平台`、`expense_subtype=平台代理费`。
- 失败路径：修复前的直接 API 请求“平台 + 律师见证费”真实复现为错误 201，并留下故意失败记录；修复后以新标题重试返回 `422`，详情“平台费用的代理费类型只能是平台代理费”，且无第二条无效记录。
- 新系统截图：
  - `new-system/01-single-option-horizontal.png`，106631 字节，SHA256 `e405ac73d88cfafbfbda78bfc9fa8a7c288883895e99c340fa51802ae19a7795`；唯一候选横排显示。
  - `new-system/02-platform-agency-created.png`，114501 字节，SHA256 `755fd78440c85a8540037d2f6c46a5e5ea99b7c2088e2c584f851d8c3034d4fa`；新增后列表记录。
  - `new-system/03-refresh-persistence.png`，114501 字节，SHA256 `755fd78440c85a8540037d2f6c46a5e5ea99b7c2088e2c584f851d8c3034d4fa`；刷新并重新进入后的持久化记录。
- 上述五张旧/新系统截图均已再次逐张原始分辨率视觉复核，画面非空且与说明一致；Chrome 会话已 finalize，未遗留本任务标签页。

## 清理与边界

- SQLite 事务删除业务记录 id `1,2,3,4`（含正常验收记录及修复前故意失败记录）、关联 workflow events/finance transactions，以及重复主数据 `CODEX-901-R34-PLATFORM-DUP`；删除后对应业务记录、参数、事件、交易计数均为 0，基础管理员保留。
- 精确停止 PID `45808`（API）和 `2672`（前端）；端口 `18034`、`15434` 均无监听。
- 删除临时 `apps/admin-web/.env.local`；隔离 `runtime` 目录及 SQLite/日志均不存在，不进入 Git。
- 清理时 Git 对统一忽略的证据父目录作了扩大匹配；随后从本机会话缓存按原始截图字节恢复全部 8 张图片。源图哈希与工作簿首次提取值完全一致，旧/新截图字节数与首次验收记录一致，并已重新逐张视觉复核。该恢复不改变验收内容。
- 未修改正式版本、tag、`origin/dev`、线上数据库、8089 部署或 Excel 完成状态；未处理第35—37行。
