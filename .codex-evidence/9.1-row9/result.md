# 9.1 第9行整改结果

- reading-confirmation：已读取第9行全部文字并逐张查看 C9 两张新系统问题图；未读取第10行。
- 原问题：编辑本人姓名应排除自身；其他账号精确同名必须阻断；相似姓名不得误判。

## 旧系统只读实跑

- 账号/角色：`admin` 管理者；路径 `人事中心 → 员工管理`，URL `/8001002/HR/Staff/List`。
- 原入口查询用户名 `fwl`，旧系统返回员工号 415、用户名 `fwl`、中文姓名“范文玲”、审核部。只打开修改入口，不保存、不提交、不写旧库。
- 截图中的新系统迁移数据与本地旧动态样本不完全相同，因此旧系统动态数据未完整复现；以同角色、同入口可达步骤、原截图及源码控制器共同审计。
- 证据：`legacy-staff-self-record-readonly.png` 已保存、非空并经 `view_image` 目视确认。

## 根因与修改

- 既有 `_require_unique_hr_display_name` 对正式 HR 档案已正确排除当前 `employee_id` 与关联账号，并使用规范化精确相等。
- Chrome 实测发现列表中的 fwl 是尚未补建正式 HR 档案的系统账号（负数虚拟 employee id），编辑走 `/system/users/{user_id}`；该分支原先直接赋值 `body.display_name.strip()`，绕开唯一性门禁，实际可错误保存为 admin 已占用的“陶威”。
- 修改 `apps/api-server/app/main.py`：系统账号更新 display_name 同样调用 `_require_unique_hr_display_name(..., linked_username=user.username)`，仅排除本人，阻断其他账号精确同名。
- 测试文件：`apps/api-server/hr_display_name_self_edit_row9_test.py` 新增系统账号编辑分支契约。

## 隔离新系统 Chrome 验收

- 实例：API `127.0.0.1:19165`、Web `127.0.0.1:19166`、隔离 SQLite `.codex-runtime/row9/legal-platform-row9.db`；账号 `admin`。
- 本人成功/刷新：fwl 保持本人姓名“范文林”，只修改手机号为 `13900009009`，提示“系统账号资料已更新”；返回列表后仍显示 fwl / 范文林及新手机号。证据 `local-self-name-save-success.png`。
- 失败路径：再次编辑 fwl，把姓名改成 admin 精确占用的“陶威”，保存被阻断并提示“中文姓名已存在”，弹窗保持打开。证据 `local-exact-duplicate-blocked.png`。
- 相似名成功/刷新：改为未占用的“范文林一”保存成功，返回列表刷新后显示 fwl / 范文林一，证明不是包含匹配。证据 `local-similar-name-refresh-success.png`。
- 清理：随后从同一编辑入口把 fwl 恢复为“范文林”；最终关闭本行 Chrome、停止服务并删除整份隔离库，因此手机号与姓名验收变更均不残留。

## 测试与建议

- `python apps/api-server/hr_display_name_self_edit_row9_test.py`：3/3 通过。
- `python -m py_compile apps/api-server/app/main.py`：通过；`git diff --check`：通过。
- 构建/部署/版本/线上写库：均未执行。
- 数据库补丁建议：只读生成同一 username 多档案及规范化姓名冲突清单，人工确定主档；不要自动合并或删除。增加姓名唯一索引前必须先清零存量冲突。
