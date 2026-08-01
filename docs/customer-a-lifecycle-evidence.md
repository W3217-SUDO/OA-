# 客户中心 A 闭环浏览器验收证据

## 页面与标签

- 旧站只读页：`https://sh.021ipr.com/Console/Index`，标题“我的客户”；可见客户管理/我的客户入口与 iframe，未执行创建、编辑、保存、上传、下载或删除写操作。
- 本地 dev 页：`http://127.0.0.1:5173/?page=customer-new` / `?page=customer-mine`。浏览器恢复后只保留旧站 1 个、本地 1 个标签。

## 已完成的本地真实操作

- 新建客户 `CODEX-CUSTOMER-A-1785596049275`：空名称保存显示“请输入客户名称”；同名再次保存显示“客户名称已存在，不能创建或改为同名客户”；合法保存显示“客户已创建”。
- 查询列表真实回显该客户（编号 `SHKH2600001`），点击名称进入查看页，回显名称、编码、类型、建档日期、管理人及联系人/事项记录/客户文档标签。
- “更多操作 → 客户编辑”打开真实编辑对话框；输入简称后取消，重新打开确认未落库；再次保存 `CODEX-CUSTOMER-A-EDITED`，重新打开确认回显。
- 独立客户 `CODEX-CUSTOMER-A-CHILD-1785596396842`：联系人 `CODEX-CUSTOMER-A-CONTACT` 新增、编辑为 `A-EDIT-POSITION`、确认删除；事项记录 `CODEX-CUSTOMER-A-NOTE` 新增并删除；客户文档 `CODEX-CUSTOMER-A-DOC.txt` 上传成功。
- 文档“查看”按钮已实际点击且页面无错误提示；浏览器下载事件等待超时，未以事件作为成功依据。随后使用同一授权 `admin` 会话 HTTP 验证：状态 `200`，`Content-Disposition: attachment; filename="CODEX-CUSTOMER-A-DOC.txt"`，类型 `text/plain; charset=utf-8`，长度 `26`，下载 SHA-256 与源文件均为 `7725e20689fe82773891c5bdf9cff83b7d4796979ed1ba02a54f3334c564e479`。
- 关联入口（只读既有客户）：本地客户列表中合同数量按钮实际点击后跳转到 `http://127.0.0.1:5173/?page=contract-company`，目标页显示合同列表与分页；对应只读 API 记录 `id=44` 回显合同编号 `CODEX-CONTRACT-C-20260801231146-CON`、名称 `CODEX-CONTRACT-C-20260801231146-CONTRACT`、状态“已通过”。该数据属于其他线程，未修改或清理。
- 既有客户 `SHKH1810649 / test` 的只读 API 关联核对显示合同 `SHHT2610035`、`SHHT2510026`、`SHHT1810328` 共 3 条，案件 0 条；本地合同数量按钮因此有真实目标，案件数量应进入无数据路径，未虚构案件详情。
- 继续点击合同列表中的 `SHHT2610035`，真实跳转到 `http://127.0.0.1:5173/?page=contract-detail-14-SHHT2610035`，详情页回显合同编号，并展示合同标的/审批及回款、开票、付款等字段区域。
- 点击同一客户案件数量 `0`，真实跳转到 `http://127.0.0.1:5173/?page=case-company-civil`，页面显示“暂无数据”空态；未伪造案件详情。
- 旧站同步只读快照：URL `https://sh.021ipr.com/Console/Index`、标题“我的客户”，可见“客户管理/我的客户”与 iframe；未执行旧站写操作。

## 清理

- 仅清理本线程创建的客户记录 ID `35`、`39`、附件 ID `6`；先经本地客户回收接口，再精确删除 SQLite 记录及附件文件。
- 复核：`business_records` 中 `CODEX-CUSTOMER-A-%` 为 0，`file_attachments` 中对应文件为 0，上传文件与临时源文件均不存在。

## 尚未完成/阻碍

- 关联合同列表→合同详情及案件入口→明确空态均已完成真实点击证据；旧站只保留入口/iframe 可见性证据。
- 旧站客户 iframe 读取能力受限，仅记录入口与可见控件，严格保持只读。
