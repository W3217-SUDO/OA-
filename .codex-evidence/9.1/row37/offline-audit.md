# 9.1 第37行返工离线审计

## 原整改意见与全部返工意见

- 原整改：案件“文档信息”增加“生成操作”和“更多操作”；生成菜单按旧系统配置；更多操作须实查旧系统；删除严格限制为本人只能删除本人上传文件。
- 返工（F37 红字）：生成入口虽然出现，但正式文档模板没有上传，不能据案件信息生成相应模板文件；暂时保留入口，后续模板到位再直接套用。
- 返工图（G37）：证明上一轮十项菜单已出现，但不能证明下载文件为正式模板，也不能证明删除、申请用印、更改目录的真实动作闭环。

## 旧源码与数据关系

- 旧视图：`Areas/Legal/Views/CaseFile/PartialView/CaseFileList.cshtml`。
  - 生成操作十项分别调用 ArchiveLetter、AuthorizationLetter、一审/二审/执行 LawyersLetter、IdentificationLetter、SettlementList、CompensationLetter 的 Create。
  - 更多操作调用 `CaseFile.Delete`、`OfficialDocument.CreateByCase`、`CaseFileTypeChange`。
- 旧控制器：`Areas/Legal/Controllers/CaseFileController.cs`。
  - 各生成端点先按案件字段校验，再由 `CaseLetterBaseProcessFactory`/对应流程导出 Word；单案件将导出字节持久化为案件文件，上传人为当前登录账号。
  - 删除由 `CaseFileDelete` 进入服务层；更改目录由 `CaseFileTypeChange` 进入服务层。
- 待 Chrome 实跑补齐：原案件入口、原角色可达性、三个更多操作的页面反馈；禁止确认任何删除、用印或目录变更，也禁止触发会实际生成文件的旧系统写操作。

## 上次代码与测试审计

- 上次主要变更：`9667e45 fix: make case document generation actions reliable`，改善菜单点击隔离、重复点击保护和生成后附件刷新。
- 更早实现：`2fc9314 fix: restore legacy case document operations` 等，补齐十项生成、删除/用印/移动及后端端点。
- 当前新系统生成端点不是读取已上传的正式模板，而是 `_case_document_bytes` 用 python-docx 自行拼装内容。这与 F37 所说“模板未上传、后面直接套模版”存在范围差异。
- 当前删除端点先读取整批附件，逐项校验 `item.uploader == identity["username"]`，任一他人文件即 403，所有校验完成后才删除，因此管理员也不能越权且混合选择不会部分删除。
- 当前移动端点限制为当前案件文件、有效目录，并写工作流审计；申请用印会以单个所选附件创建正式发文草稿，须在浏览器确认入口与字段。

## 上次误判原因

1. 把“菜单出现、生成接口成功、能下载自行拼装 DOCX”当作“正式模板生成已闭环”，没有以 F37 的模板资产边界核对产物来源。
2. 浏览器证据侧重生成入口/刷新，没有对原问题要求的三个更多操作逐项留下证据。
3. 删除所有权虽已有后端自动化测试，但仍须在原问题案件用两个不同上传人完成浏览器成功/失败路径，不能只凭源码和接口测试宣称整行完成。

## 离线聚焦测试

- 前端：`node --test caseDocumentAction.test.mjs caseDocumentOperationsRow5.test.mjs`：9/9 通过。
- 后端：`python -m unittest case_document_operations_row5_test.py case_document_generation_row13_test.py -v`：6/6 通过。
- 覆盖：十项菜单；生成防重复/列表刷新；十类可下载 DOCX；缺字段原子失败；本人删除成功、混选他人文件整批 403；目录移动及审计。
- `git diff --check`：通过。

## 本次离线结论与逐项确认单

1. 十项菜单名称：源码/测试一致，待旧系统与新系统 Chrome 逐项截图。
2. 正式模板：未闭环。当前实现为程序拼装 DOCX，不得表述为“已套正式模板”；按返工意见保留入口，正式模板资产到位后另行替换。
3. 删除本人文件：后端测试通过；待新系统原问题案件浏览器成功路径与刷新/物理附件结果。
4. 删除他人文件：后端混选原子拒绝测试通过；待新系统原问题案件浏览器 403 提示与无残留验证。
5. 申请用印：代码已连接正式发文草稿接口；待旧/新 Chrome 只打开流程并核对，不提交。
6. 更改目录：后端移动、审计测试通过；待新系统浏览器选择保存、原位刷新，并清理恢复测试数据。
7. 旧系统动态流程：Google Chrome 已打开 `localhost:8091`，但有效旧系统身份缺失，停在登录页；证据见 `old-system-run.md` 与 `old-system/login-blocked.png`。旧系统动态数据未完整复现，不得写成浏览器通过。

## 文件与提交状态

- 第37行新增证据：`reading-confirmation.md`、`offline-audit.md`。
- 当前未修改第37行业务代码；不应为迁就缺失模板而伪造模板资产。
- 按主会话要求未 commit/push。
