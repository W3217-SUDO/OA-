# 8.28 第24行本地验收

- 问题：客户列表展示的合同/民事案件数量与点击进入后的关联列表不一致。
- 根因：客户关系跳转同时携带客户 ID 与客户编号，后端在兼容“ID/编号/名称任一关联”之后又强制客户编号，排除了仅保留客户名称的迁移记录；合同页面同时可能残留上次搜索条件。
- 修复：客户 ID 关系查询统一兼容 ID、编号、精确客户名称；存在明确客户关系时不再叠加客户编号条件；关系跳转替换并清空旧合同搜索条件；数量口径排除归档合同并与点入列表一致。

## 自动测试

- 后端专项：`python -m unittest customer_count_navigation_row24_test.py`，1/1 通过。
- 后端编译：`python -m py_compile app/main.py customer_count_navigation_row24_test.py`，通过。
- 前端专项：`node --test customerCountNavigationRow24.test.mjs`，3/3 通过。
- 生产构建：`npm.cmd run build`，通过；版本保持 1.1.27，5637 modules transformed。
- 既有组合测试 `customer_count_scoped_navigation_contract_test.py` 中3项通过、1项因基线测试账号缺少合同新建动作权限返回403；该失败与本行关系筛选差异无关，未修改权限基线。

## Codex 内置浏览器

- 客户 `CODEX-828-R24-客户` 显示合同数2、民事案件数2。
- 点击合同数后显示2条：一条 ID 关联、一条仅名称关联；归档合同及相似客户合同均未出现；旧搜索条件“目标商标”已清除。
- 点击民事案件数后显示2条：一条 ID 关联、一条仅名称关联；相似客户案件未出现。
- 证据：`browser-contract-count-navigation.png`、`browser-civil-case-count-navigation.png`。

## 清理

- 本地验收数据前缀：`CODEX-828-R24-`。
- 本行不包含数据库结构迁移或正式数据补丁。
