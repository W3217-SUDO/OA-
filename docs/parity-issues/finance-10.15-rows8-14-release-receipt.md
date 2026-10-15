# 10.15 第8至14行发布回执（1.1.437）

- 发布提交：`c4ca87b864a81320178dafe86c668a045ca42da5`
- GitHub：`dev` 已同步；`main` 快进被远端非 fast-forward 拒绝，未强推，待项目负责人处理历史分叉。
- 版本：`1.1.437`
- 运行包：623 个正式文件；本地 runtime build/verify 通过；服务器严格 verify 通过；manifest SHA256 `6dd8682b489b0df6a3a97944804e39868486f88ae6bd504f52103dae2e8bb959`。
- 生产激活：`/opt/sunhold-oa/runtime/enterprise/packages/1.1.437`，current 已指向该目录；`sunhold-oa-api`、`sunhold-oa-web` active；`/health` 返回 `{"status":"ok"}`；`build-info` 返回版本和提交一致。
- 浏览器：当前已登录工作台标签在 `finance-internal-archive` 验证到全局搜索、财务菜单、筛选首行、15 行/页、35 页和合计数据均可见；`finance-payment-print` 入口可打开，但当前真实数据处于加载/无 CODEX 单据，打印与导出文件回读未证明。
- 第8至14行：定位文档已完成并推送；本轮代码覆盖付款 Word 抬头/银行字段、付款详情复制入口、银行到账删除角色和终态后端门禁。I8-I14 暂不写 `1`，等待专属 CODEX 数据的接口/数据库/文件回读和逐行浏览器闭环。
- 已知限制：本地隔离后端完整回归仍有 266 项待隔离环境验证；不把该项或服务健康替代业务验收。
