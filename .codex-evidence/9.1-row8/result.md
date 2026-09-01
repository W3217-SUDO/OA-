# 9.1 第8行整改结果

- reading-confirmation：已读取第8行全部文字并查看 C8 唯一锚定原图；未越行读取后续问题。
- 根因：`PlatformFinancePage.tsx` 曾在回款单位 `AutoComplete.onSelect` 写入 `customer`，又在客户 `Select.onChange` 反向写入 `payerName`，造成两个独立业务字段双向强绑定。
- 修改：删除两处跨字段赋值。回款单位可自由输入或接受客户目录建议，但只影响回款单位；客户为独立、可清空选择。客户为空时后端只登记到账，不调用 claim，进入未认领公海。
- owned files：`apps/admin-web/src/PlatformFinancePage.tsx`、`apps/admin-web/receiptPayerCustomerIndependenceRow8.test.mjs`。

## 旧系统只读实跑

- 账号/角色：`admin`，管理者，具备财务菜单与新增回款入口。
- 路径：`财务中心 → 回款管理 → 新增回款`，URL `/5001001001/FAM/AR/PaymentCreate`。
- 操作/结果：仅填写回款单位 `CODEX-R8-PAYER`，客户仍显示“请选择客户”；未保存、未提交、未写旧库。
- 证据：`legacy-receipt-fields-independent-readonly.png`。

## 隔离新系统 Chrome 验收

- 实例：API `127.0.0.1:19155`、Web `127.0.0.1:19156`、隔离 SQLite `.codex-runtime/row8/legal-platform-row8.db`；账号 `admin`。
- 失败路径：空表单直接提交，同时提示“请输入回款单位 / 请输入回款金额 / 请选择回款方式”，未产生记录。
- 字段独立：回款单位填写 `CODEX-901-R8-UNCLAIMED` 后，客户名称保持“请选择客户”，提示“没有匹配的系统客户”。证据 `local-payer-filled-customer-empty.png` 已保存、非空并经 `view_image` 目视确认。
- 成功/刷新持久化：金额 `88.08`、方式“银行转账”、客户留空，提交成功；重新进入回款管理后，客户名称和客户管理人均为 `—`，未分金额 `88.08`，证明保存为未认领回款。证据 `local-refresh-unclaimed-customer-empty.png` 已保存、非空并经 `view_image` 目视确认。
- 建议选择仍独立：在回款单位建议中选择系统客户“测试555｜KH-ROW5-RESTORED-TEST555”后，回款单位为“测试555”，客户名称仍为“请选择客户”。证据 `local-payer-suggestion-selected-customer-empty.png` 已保存、非空并经 `view_image` 目视确认。
- 反向独立与第二条持久化：保持回款单位 A“测试555”，在客户名称中另选客户 B“test｜SHKH1810649”，选择后回款单位仍为“测试555”；以金额 `99.09`、银行转账保存，提示“回款登记并认领客户成功”。刷新回款管理后同一行明确显示客户 `test`、回款单位 `测试555`、金额 `99.09`。选择态证据 `local-payer-a-customer-b-independent.png`、刷新证据 `local-refresh-payer-a-customer-b.png` 均已保存、非空并经 `view_image` 目视确认。

## 测试与清理

- `node apps/admin-web/receiptPayerCustomerIndependenceRow8.test.mjs`：通过（1/1）。
- `git diff --check`：通过。
- 两轮共验证一条客户留空回款及一条“回款单位 A / 客户 B”回款；每轮均使用新复制的隔离 SQLite。最终本行 Chrome 标签已关闭；19155/19156 已停止；隔离 SQLite、启动脚本和上传目录整份删除，两条验收回款均不残留。
- 构建/部署/版本/线上写库：均未执行。
- 数据库补丁建议：无结构补丁。可只读复核历史“创建后立即自动认领”的记录，但不能仅因付款方与客户同名判错或批量清空客户。
