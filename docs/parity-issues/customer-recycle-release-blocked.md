# [本地修复，待验收] 客户回收站的进入公海被接口阻断

## 前端位置
- 发现日期：2026-09-12；来源：主动审计，不是用户新增表格条目。
- 菜单：客户管理 -> 个人回收站、部门回收站、公司回收站 -> 更多操作 -> 进入公海。
- 路由：customer-recycle、customer-dept-recycle、customer-company-recycle。
- React：crm/CustomerCenterPage.tsx，originalActionItems -> runOriginalAction -> releaseCustomer 确认框 -> action -> POST /customers/{id}/release -> load。
- 客户删除确认框还明确提示“可在回收站恢复或进入公海”。

## 新旧对比与依据
- 旧 CustomerList.cshtml 的 PageId 6001002、6001004、6001010 均有有效 InOpen 按钮。
- 旧 Scripts/CRM/Customer/CRM.Customer.js:164 的 InOpen 直接调用 CustomerOpen，成功刷新列表；没有先恢复的前置请求。
- 旧 CustomerController.cs:539-546 转交 OpenCustomer。业务程序集内部实现本轮未获取，不能声称完整旧服务已验证。
- 新 release_customer 把“公海”和“已回收”一起作为 409 阻断条件，导致三个前端入口必然失败。
- 项目 scripts/smoke-api.py:890、990、1183 已明确要求回收站释放成功及重新拾回；但 customer_backend_alignment_d6_contract_test.py 的相反断言固化了错误。源码静态审计检查冒烟代码存在，未真正运行这条链，不能证明功能通过。

## 整改与验证计划
- 先使用独立内存 SQLite 和真实 ASGI 请求复现，再仅移除 release 中“已回收”的错误阻断。
- 保留重复释放拒绝、可见性查询、行锁、归属更新、共享清空、日志和事务；不扩大角色权限或修改旧系统。
- 三种回收站分别核对列表消失、公海出现、重新拾回后归属与部门、日志状态；重复释放与无权访问不得产生写入。恢复流程另做回归。
- 修正 D6 的错误状态断言；不运行会清理共享 SMOKE 数据的原脚本。
- 未浏览器验收、未提交、未部署。暂不改 customer_managers 的释放期历史展示，拾回仍使用现有管理人替换逻辑。

## 复现与改动
- 修改前定向 HTTP 测试实际失败：GET 回收站能查询到记录，POST release 返回 IsSuccess=false / 当前客户状态不能释放到公海，未变成公海状态。
- release_customer 的拒绝条件仅保留已经公海，不再阻断已回收。其余逻辑保持不动，未绕过可见性或状态保护。
- D6 回归测试按三个实际回收站入口及既有 smoke 流程修正错误断言；新增 customer_recycle_release_test.py 和 customerRecycleRelease.test.mjs 验证数据流程及真实前端处理函数。

## 交接时状态
- 用户要求换智能体，停止新增排查，详细断点见 `../AUDIT-HANDOFF-2026-09-12.md`。
- 后端 `customer_recycle_release_test.py`：6/6 通过。原 5/7 的两项失败已收尾：修正了非 admin 对公海 restore 得 403 的错误断言（按真实权限契约区分角色期待）；新增 `test_page_menu_capability_owner_flow` 覆盖菜单能力身份路径的完整释放-拾回流。
- 前端 `customerRecycleRelease.test.mjs`：6/6 通过。
- D6 定向两项（`test_release_accepts_migrated_and_recycled_status_but_rejects_public`、`test_recycle_blocks_customers_with_linked_contracts_or_cases`）：通过。
- 完整 D6 回归 16 项中 1 项失败（`test_guid_events_and_files_list_and_download`），与本轮无关，为预先存在的 GUID 文件下载路由问题。
- 其他全部本轮 API 测试 29/29 通过、前端 16/16 通过、菜单审计 0 未处理、API 覆盖 822/822、前端构建 v1.1.108 通过。
- 仍未浏览器验收、未提交、未部署。
- 残余风险：真实登录身份链的 `_page_menu_capability` 注入路径仅单元测试覆盖，未经过真实认证中间件端到端验证。
