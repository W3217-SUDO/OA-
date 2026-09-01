# 9.1 第7行结果

- reading-confirmation：已逐格读取第7行文字并查看 C7 唯一锚定原图；未读取 9.1 工作表后续行。
- 旧流程审计：旧源码 `CreateUpdate.cshtml` 按 `Coordinator` 逗号顺序渲染标签；`CRM.Customer.js` 的 `Coordinator.AddIn` 把新标签插到输入框之前，因此当前 DOM 顺序为既有标签后追加新标签，保存时又按 DOM 顺序生成 `Customer_CustomerBasic_Coordinator`。旧源码本身不满足本行明确的新排序要求，用户整改意见优先。
- 上次实现审计：新前端 Ant Design `Select mode="multiple"` 原样提交选择顺序；后端 `/customers/{id}/managers` 原样保存 `body.managers` 并把第一项设为 owner，所以新选人员也一直排在末尾。
- 根因：前后端均把多选控件的追加顺序当作业务优先级，没有区分既有管理人与本次新增管理人。
- 修改：前端表单在每次选择变化时，以编辑开始时的管理人列表为基准，将本次新增人员逆序压到最前，既有仍保留者按原顺序后移。Chrome 端到端发现前端已经输出“最新优先”数组，后端若再次 `reversed(added)` 会发生双反转；后端现改为尊重请求中的优先顺序，仅把新增块置于保留项之前。另修复通用客户编辑动作门禁没有接受管理员通配符 `*`、导致管理员真实保存被 403 阻断的问题。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/customer_manager_newest_first_row7_test.py`、`apps/api-server/job_role_permission_policy_contract_test.py`、`apps/admin-web/src/CustomerCenterPage.tsx`、`apps/admin-web/customerManagerNewestFirstRow7.test.mjs`。
- 本人 Chrome 验收：旧系统以本地 `admin/管理者` 只读进入 `/6001001/CRM/Customer/CustomerList` 与 `/6001000/CRM/Customer/CreateUpdate`，确认我的客户和客户管理人入口，未保存/提交/写库；原截图客户本地旧库不存在，使用同业务角色可达入口并注明动态原记录未复现。新系统独立 19145/19146 + SQLite，以客户 `SHKH1810649` 原管理人陶威、范文林，依次新增 ROW7-A、ROW7-B；编辑态立即显示 `ROW7-B、ROW7-A、陶威、范文林`，保存后刷新公司客户列表仍保持该顺序。随后以最新 owner ROW7-B 删除 ROW7-A，保存并重复保存，数据库持续为 `row7b,admin,fwl`、未反转；最后通过页面删除 ROW7-B 并保存，恢复 `admin,fwl`。
- 直接证据：`legacy-customer-list-readonly.png`、`legacy-customer-manager-create-readonly.png`；`local-edit-newest-managers-first.png`、`local-save-newest-first-success.png`、`local-refresh-persisted-list.png`。最终三张新系统证据均保存为非空 PNG，其中编辑态和刷新列表已目视确认清楚显示顺序。
- 失败路径：首次保存真实触发“当前角色没有编辑该业务模块的动作权限”，据此修复管理员 `*` 动作通配符门禁并重验成功；该失败未冒充通过。
- 测试：后端 `customer_manager_newest_first_row7_test.py + job_role_permission_policy_contract_test.py` 共 6/6 通过；前端 `customerManagerNewestFirstRow7.test.mjs` 通过；`py_compile` 与 `git diff --check` 通过。
- 构建/部署/版本/线上数据库：均未执行。
- 数据库补丁建议：不建议批量重排历史客户管理人，因为无法从现存数组可靠推导每人的新增时间；新逻辑从后续编辑开始生效。若业务必须迁移，只对 `assignment_history.managers/created_at` 完整的客户按时间重建，并先导出候选清单人工确认。
- 主会话 Chrome 验收：打开一个至少已有两名管理人的隔离测试客户；依次新增第三、第四名，确认标签立即成为“第四、第三、原第一、原第二”；保存并刷新后顺序不变，列表第一管理人/owner 为第四名；删除第三名再保存确认其不回填；不改人员再次保存确认顺序不反转；最后恢复原管理人列表并核对 assignment_history。
