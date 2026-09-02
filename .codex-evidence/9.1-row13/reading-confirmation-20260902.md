# 9.1 第13行结构化读取确认（2026-09-02）

工作表：9.1
行号：13
扫描范围：A:I（工作表实际使用范围 A1:I37）

## 全列原文

- A：`调查大厅`
- B：`调查大厅里面，我发布的调查任务，这里面的“我的调查任务”和“过期调查任务”指的是品管根据客户的合同发布的调查任务，这个调查任务是发给调查主管的，不是发给调查员的，也不是自己需要去调查的任务，所以这里界面理解就有问题，这里只有刷新、修改和上传调查资料三个功能，并不需要上传线索的功能，具体界面看老系统截图`
- C：空文字；锚定图片 `C_image430.png`，1912×917。新系统截图：品管/发布方入口“我发布的调查任务 → 我的调查任务/过期调查任务”，底部错误包含“新增线索”等操作。
- D：空文字；锚定图片 `D_image431.png`，1920×944。旧系统截图：同类“我的调查任务”列表底部仅“刷新 / 修改 / 上传调查资料”。
- E：`2026.9.1`
- F：空
- G：空
- H：`1`（本次委托明确返工，不作为完成依据）
- I：空

## 批注、格式与图形

- A:I 均无批注、无超链接；第13行无合并单元格，行高 149.25。
- A–E 为细边框表格样式；B 自动换行并垂直居中；F/G/I 为空白默认样式；H 为普通数值格式。
- 本行只有 C13、D13 两张锚定图片，已逐张按原始分辨率核对；未遗漏浮动图形。

## VibeHub 脱敏术语核对

- 脱敏候选：`任务发布视图`、`角色职责`、`操作权限`。
- resolver revision：`d2034b1998eaaa2f`；前两项 0 候选，“操作权限”只匹配到“身份认证”，与本行定位不一致，故不采用。
- 记录：核对已执行，无需添加可靠术语，原文保持不变。
- 专业定位表达：发布方任务列表属于调查任务的委派与管理视图，目标对象是调查主管而非执行调查员；该视图的操作集合应限定为刷新、修改和上传调查资料，不应暴露执行环节的线索新增能力。

## 旧系统同入口、源码与数据

- Google Chrome 访问 `1401001002/CIT/Investigation/List`（我的调查任务）和 `1401001003/CIT/Investigation/List`（过期调查任务）；当前登录发布人归属下均为空，分别保存 `legacy-publisher-active-empty.png`、`legacy-publisher-overdue-empty.png`，不把空列表冒充原记录动态通过。
- `GD.CRM.WEB/Areas/CIT/Controllers/InvestigationController.cs` 对两个 PageId 都强制 `BusinessOwner=LoginHelper.GetUserName()`；`Views/Investigation/List.cshtml` 对两个 PageId 只输出刷新、修改、上传调查资料。
- 本地旧库 `PRD_CRM_GD_20200211` 只读查询：`Legal_Investigation` 共 119 条有效记录；当前账号归属仅 1 条且已过期，但仍被其他状态条件排除。权威字段为 `InvestigationNo`、`AuthorizationBeginTime/EndTime`、`BusinessOwner`，调查主管/执行关系另由 `Legal_Investigation_Task` 承载。未写旧库。

## 新系统源码、数据与根因

- `InvestigationCenterPage.tsx` 将 `investigation-task-mine/overdue` 映射为 `module=investigation + investigation_view=published`；按钮集合均只含查询、刷新、修改、上传调查资料；新增线索只属于 `investigation-task-sub-mine`。
- `app/main.py:list_records` 对父调查 published 视图按 `data.publisher=当前用户` 查询，历史缺 publisher 时才以 owner 兼容；过期页再按 `authorized_to < 今天` 且未完成/取消过滤。
- 隔离 SQLite 两条父调查数据均由 `row13publisher` 发布、负责人为 `row13supervisor`；一条授权到 2027-09-01，一条授权到 2026-08-01。父调查与调查主管关系没有被改写成调查员子任务。
- 具体根因：旧实现把发布人的父调查管理页错误映射成调查员子任务执行页，导致模块、归属投影和动作集合同时错位，暴露新增线索/关闭报告等执行动作。
