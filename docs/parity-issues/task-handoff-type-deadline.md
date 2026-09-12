# 任务交接未接入旧类型期限上限

2026-09-13；状态：已完成本地代码与隔离测试，未提交、未部署、待用户验收。

- 前端：事务中心 -> 任务详情/列表 -> 交接，tp/TaskActionModals.tsx 的 HandoffModal；案件任务点击详情后的同类动作。
- 旧证据：S/TP/Task/TaskNodeService.cs:53-71，创建下一节点时读取任务类型 SkipDays，限制 NodeEndTime；保存新节点负责人、协作人和节点链。来源根目录见 legacy-auto-task-rules-20260913.md。
- 本地实现：新增 `app/core/task_type_rules.py`，仅为已查实的 28 个旧 TypeId 解析交接 `SkipDays` 上限；兼容 `legacy_task_type_id`、`TaskTypeId`、旧投影及已知 `auto_task_type`。未知类型没有静态默认。可选覆盖仅接受 `SystemParameter.category=legacy_task_type` 且 `code` 为已查实 TypeId 的 `skip_days`/`SkipDays`，不从泛用参数或 `extra` 推断类型，避免误命中。
- 时间语义：`TaskHandoffInput.end_at` 和前端交接输入均为 DateTime。上限严格保留旧 C# `NodeEndTime.Subtract(now.AddDays(SkipDays)).Days > 0`：候选结束时间仅在超过上限的**完整天数**大于零时截断；`+12h` 不截断，`+24h` 截断到上限。`GapDays` 未用于生成或交接期限。
- 新接口保护：显式提交的结束时间会拒绝早于当前时间或不晚于任务开始时间；这是一项新接口输入校验，旧 `TaskNodeService` 尚未在本轮证据中证明有同等阻断，不能表述为旧行为完全对齐。旧请求仅传 `recipient/comment` 时，已识别类型会在不制造 `start_at >= end_at` 的条件下收紧既有结束时间；保留用户要求的交接后 5 日未开始自动完成。
- 验证：`task_handoff_type_deadline_test.py` 使用内存 SQLite，覆盖已知类型、旧别名、自动类型映射、参数覆盖、未知类型、旧请求、实际回传结束时间、非法开始/结束区间及冻结时间的 `+12h/+24h` 边界；未写入业务数据库。
- 边界仍未实现：新系统仍是原任务原地交接，不建立旧系统的独立节点链、协作人节点和历史节点查询；本轮未修改权限、自动任务生成或调度。
