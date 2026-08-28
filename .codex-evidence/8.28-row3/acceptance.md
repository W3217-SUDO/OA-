# 8.28 第3行本地验收

## 变更

- 从案件详情删除“历史合同”页签和专用组件加载入口。
- 合同详情、客户详情的历史合同能力保持不变。
- 案件详情默认页签继续为“文档信息”。

## 自动化验证

- `node --test caseHistoricalContractTabRow3.test.mjs`：2/2 通过。
- 第2行受影响回归：3/3 通过。
- `npm.cmd run build`：通过，Vite 5637 modules transformed；仅有既有 chunk size warning。

## Codex 内置浏览器

- 本地案件 `SH191000382B` 详情正常加载。
- `历史合同` tab 数量：0。
- `文档信息` 的 `aria-selected`：`true`。
- 浏览器日志中 `legacy-contract-history` 请求或 `Historical contract` 错误：0。
- 截图：`C:/Users/Administrator/Desktop/OA系统/问题/_返工验收/8.28_第3行/local-history-tab-removed.png`。

本行未创建业务测试记录。验收结束后 8098/5301 临时服务均停止。
