# 自动任务仅更新状态时可能未提交事务

2026-09-13；状态：已本地修复，隔离数据库跨会话验证通过；未部署。

- 前端：案件详情 -> 案件任务 -> 状态；表现候选为业务条件已满足，但下轮刷新任务仍未完成。
- 新源码：apps/api-server/app/core/tasks.py:1110 的 _finish_legacy_auto_task 只修改对象并添加消息，不提交；:1450-1453 的 _apply_case_automatic_task_rules 仅在任务总数增加时 commit。
- 调用方：apps/api-server/app/core/system.py:1023 的后台循环，以 SessionLocal 会话执行规则；后面没有补充 commit。
- 风险路径：本轮所有任务都已存在，只触发完成或其他字段变更，没有新增任务，changed=0，离开会话时未提交更新。不得仅以函数内对象状态正确判定落库成功。
- 旧对应：TaskService.Finished 在 TransactionScope 中更新任务/节点及消息并 Complete；旧行为证据见 legacy-auto-task-rules-20260913.md。
- 整改：`_apply_case_automatic_task_rules` 成功扫描后统一提交，返回值仍为新增任务数。异常仍由外层调度器回滚；不能用db.dirty/new替代提交条件，因为通知查询前的flush可能已经清空这些集合。
- 已验证：`automatic_task_legacy_agency_fee_rules_test.py` 中无新增任务、无活跃收件人且更新已flush的场景，关闭扫描会话后由新会话读到完成状态与WorkflowEvent；文书、归档、公证、退费既有完成路径同样持久化。全部使用内存SQLite，未写入业务库。
- 全局边界：这只修复已有规则的提交，不证明文书/公证等所有结束条件与旧系统完全相同。最终构建/回归和发布状态见 `auto-rules-integration-20260913.md`。
