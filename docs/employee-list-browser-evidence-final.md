# 员工列表最终轮浏览器验收证据（2026-08-01）

## 约束与页面

- 旧系统只读对照页：`https://sh.021ipr.com/Console/Index`。本轮仅打开、查看和读取列表/筛选/分页，未创建、编辑、保存、审批、上传或删除任何旧系统数据。
- 本地开发页：`http://127.0.0.1:5173/`，所有创建、状态办理、密码重置和删除均仅发生在本地。
- 浏览器旧标签在自定义控件操作超时后弃用，重新打开本地员工管理页（新 tab `finalTab4`）再继续；未复用失效 locator。

## 本地临时数据与逐项证据

使用唯一前缀 `CODEX-HR-LIST-FINAL-1785592471250-*` 创建两名员工，账号名分别为 `codex_hr_list_final_1785592471250_a/b`。创建后的列表 DOM 可见两行；B 创建成功提示为“员工档案与低权限登录账号已同步保存”。

1. A 的状态办理弹窗显示目标状态、有效日期、办理原因等字段；补齐原因后确认，页面 alert 为“人事状态及关联登录账号已同步更新”，列表重新加载后 A 行状态回显为“否”。
2. B 行点击“修改密码”，弹窗显示“修改密码：CODEX最终员工B1785592471250”和“* 新密码”；填入强密码并点击“确认重置”，弹窗关闭。密码值未写入证据，也未修改任何既有账号 hash。
3. B 行点击“系统用户”，URL 跳转为 `http://127.0.0.1:5173/?page=system-users`，页面显示系统用户列表；随后返回员工列表页。
4. A 行点击“删除”，影响检查弹窗原文为“删除影响检查：CODEX-HR-LIST-FINAL-1785592471250-A未发现关联记录，可删除员工档案及未被引用的关联登录账号。取 消确认删除”。确认后 A 行从列表 DOM 消失。
5. B 勾选行复选框，点击“删除选中”，影响检查弹窗原文为“删除选中员工影响检查所选员工均未被引用，确认后将原子删除。取 消确认删除”。确认后 B 行从列表 DOM 消失。

## 清理与复核

本地 SQLite 清理仅针对上述最终轮前缀：删除业务记录 serial_no、其 `hr_subrecords` 关联和对应 username/profile 前缀账号。清理后查询结果为：

- `users where username like 'codex_hr_list_final_%'`：0 行；
- `business_records where module='hr' and serial_no like 'CODEX-HR-LIST-FINAL-%'`：0 行；
- `hr_subrecords where data like '%CODEX-HR-LIST-FINAL-%'`：0 行。

未触碰 `CODEX-HR-SUBREC` 或其他员工数据；旧系统仍保持只读，未部署服务器。

## 验证命令

- `node --test employeeListBulkDeleteUi.test.mjs employeeBulkDelete.test.mjs employeeListLegacyPagination.test.mjs`
- `npm.cmd run build`

