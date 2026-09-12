# CRM 页面族审计矩阵（进行中）

证据日期：2026-09-12。旧页面为 `Areas/CRM/Views/Customer/CustomerList.cshtml`，查询为同区域 `CustomerController.List(ListModel model)`（PageId 分支），新列表共用 `crm/CustomerCenterPage.tsx`、`CustomerList.tsx` 和 `GET /customers?scope=...`。当前仅登记已阅读的模板/查询链，不声称全部按钮、详情、字段或真实角色已验收。

| 旧 PageId | 页面 / 新 route | 旧模板动作 | 本轮结论 |
|---|---|---|---|
| 6001001 | 我的客户 / customer-mine | 查看、编辑、删除、新增合同 | 新用户策略允许完整操作；共享保存已修复，其他动作待逐项验证 |
| 6001002 | 个人回收站 / customer-recycle | 查看、恢复、进入公海 | 新列表已定位，状态流转待专项验证 |
| 6001003 | 部门客户 / customer-dept | 查看、分配 | 分配动作已完成服务层源码级审计，见 customer-assign-parity.md；完整操作为用户策略差异，部门人员范围待专项验证 |
| 6001004 | 部门回收站 / customer-dept-recycle | 查看、恢复、进入公海 | 部门状态组合待专项验证 |
| 6001005 | 公司客户 / customer-company | 查看、分配 | 分配动作已完成服务层源码级审计，见 customer-assign-parity.md；旧控制器状态条件全置 null，新排除回收/公海；已有新策略注释，须查需求依据，不直接修改 |
| 6001010 | 公司回收站 / customer-company-recycle | 查看、恢复、进入公海 | 状态与公司范围待专项验证 |
| 6001006 | 公海客户 / customer-public | 查看、拾回 | 已通过反编译服务层源码核实，见 customer-claim-parity.md；admin 直接编辑公海客户为新系统扩展功能（旧公海页无编辑入口），按用户菜单授权策略保留 |
| 6001007 | 我的共享客户 / customer-shared | 查看 | 用户要求扩展动作保留；共享名单减少/清空已本地自动化验证 |
| 6001008 | 最近联系 / customer-recent-contact | 查看、编辑 | 日历月时间窗口已修复，6 项定向测试通过，未页面验收；见 customer-recent-time-window.md |
| 6001009 | 最近更新 / customer-recent-update | 查看、编辑 | 时间窗口同上；修改人/归属语义未改，另待需求复核 |

共享弹窗六入口复用一个实现，本轮覆盖其名单保存、人员有效性、状态阻断、日志和接收人列表反查。没有按管理员空页面推断全部流程。表中未证明项继续保留，不以文件数量或静态菜单通过作为页面对齐完成依据。
