# [本地自动化通过，待页面验收] 最近联系和最近更新缺少一个月时间范围

## 前端位置
- 发现日期：2026-09-12；来源：客户页面族主动审计。
- 菜单：客户管理 -> 最近联系的客户 / 最近更新的客户。
- 路由：`customer-recent-contact` / `customer-recent-update`。
- 具体对象：`crm/CustomerList.tsx` 的“最后联系日期”“最后修改日期”列、查询按钮和分页总数；`CustomerCenterPage` 将路由映射为 `scope=recent_contact/recent_update`。
- 接口：`GET /customers`；`areas/crm/router.py:list_customers`。

## 新旧对比
- 旧源码：`Areas/CRM/Controllers/CustomerController.cs:167-190`，6001008 分支设置 LastContactTimeBegin = DateTime.Now.AddMonths(-1)、End = DateTime.Now；6001009 对 LastUpdateTime 设置同样的范围。
- 新源码：recent_contact 只要求 last_contact_at 可解析，再按时间倒序；recent_update 按最后修改人和 updated_at 排序。完整查询链没有这两个时间区间的过滤条件。
- 差异：旧页面明确查询最近一个月，新页面可能显示更久以前甚至未来时间的数据，排序不能代替范围筛选。
- 其他差异（所有者/最后修改人、状态范围）另有历史规则和注释，本问题只先记录时间窗口，不据此擅改其他范围。

## 验证要求
- 通过真实 GET 请求检查范围内、日历月边界、边界前、未来、空值和坏日期；过滤后计算 total 和分页。
- 检查月末、闰年和时区转换，非 recent 列表及原有可见性不能受影响。

## 2026-09-12 复现与整改
- 修改前实际 HTTP + 内存数据库复现两项失败：最近联系预期 3 条返回 5 条；最近更新预期 2 条返回 4 条。过期和未来记录均未排除，影响 total 与页内结果。
- `areas/crm/router.py:list_customers` 仅对两个 recent scope 捕获一次本地当前时间，使用 calendar.monthrange 处理 AddMonths(-1) 月末；明确包含上下边界，排除未来、超期及不可解析时间。
- 联系时间使用 JSON 最后联系时间；数据库修改时间使用 updated_at。显式时区统一至 UTC 比较；无时区联系值按服务本地时间处理，无时区数据库时间按 UTC 处理，保持 SQLite/数据库返回值惯例。
- `_parse_customer_contact_at` 增加可选 naive_timezone，不改变其他调用点默认行为；本次两个列表的过滤与排序使用同一份标准化时间映射。
- 先过滤再计算 total/page_items，仍保留原有可见性、状态、最后修改人、客户名和人员查询条件；非 recent scope 不新增时间限制。
- 窗口按服务本地时区，不自动猜测或改写旧库历史日期的原始时区；混用未标注 UTC/本地字符串的数据需要单独迁移审计。

## 本地验证与后续状态
- `python -m unittest customer_recent_time_window_test -q`：6/6 通过，实际 ASGI 请求和隔离内存 SQLite 覆盖边界、月末/闰年/跨年、时区、总数分页、无关 scope、可见性与状态。
- `python -m unittest customer_share_replacement_test -q`：7/7 回归通过。两套测试使用独立内存库，未修改共享业务数据。
- TypeScript/Vite 生产构建 1.1.108、相关 Python 编译、菜单静态审计、822 处 API 调用静态匹配、`git diff --check` 均通过；构建仍有既有大资源块警告。
- 审计断言改为检查真实日历月过滤、统一排序值和过滤先于 total/分页，不再要求旧的“日期非空即入选”。
- VibeHub 已以脱敏短词“时间窗口”查询，无可靠匹配，不添加术语链接。
- 当前状态：本地自动化通过；未浏览器验收、未提交、未推送、未部署。真实服务时区和历史未标注日期仍待核实；完整 verify-local 流水线的虚拟环境缺失问题未处理。
- 后续页面验收位置：客户管理 -> 最近联系/最近更新，检查日期列、查询及分页总数；未取得页面证据前不标记“已验收”。
