"""根据 OA 的有效菜单权限生成办公入口，不按岗位名称硬编码权限。"""

from app.core.system import _record_module_menu_allowed


def workspace_commands(identity: dict) -> list[dict]:
    commands = [{"id": "today", "label": "今日工作", "prompt": "列出我今天优先处理的审批和任务，只列最重要的5项，并写明下一步", "skill_id": "general-office", "icon": "today"}]
    definitions = [
        ("task", "tasks", "我的任务", "查询我负责和发起的任务，优先列出逾期和临近截止的事项", "general-office", "task"),
        ("contract", "contracts", "合同审批", "查询我当前待审批的合同，列明待处理事项，不执行审批", "general-office", "approval"),
        ("case", "cases", "案件工作", "列出我权限内的案件和当前阶段，区分本人负责与可访问的案件", "plain-legal-brief", "case"),
        ("finance", "finance", "财务待办", "整理我权限内的财务待办和待审核事项，标明需要核对的材料", "general-office", "finance"),
        ("seal", "seal", "用印办公", "整理我权限内的用印待办和待审核事项，列出下一步处理顺序", "general-office", "seal"),
        ("customer", "customers", "客户工作", "查询我权限内的客户工作事项，先搜索真实业务接口，不推测客户数据", "general-office", "customer"),
        ("investigation", "investigation", "调查工作", "查询我权限内的调查任务和处理进度，标明需要跟进的事项", "general-office", "case"),
        ("clue", "clues", "线索待办", "查询我权限内的线索待审核事项，列出当前状态和下一步", "general-office", "case"),
        ("hr", "hr", "人事工作", "查询我权限内的人事待办和人员工作事项，只使用当前账号可访问的真实接口", "general-office", "customer"),
        ("document", "documents", "收发文工作", "查询我权限内的收发文待办，整理需要处理的文件和下一步", "general-office", "seal"),
        ("warehouse", "warehouse", "仓库工作", "查询我权限内的仓库工作和档案事项，先搜索真实接口后再读取数据", "general-office", "case"),
    ]
    for module, command_id, label, prompt, skill_id, icon in definitions:
        if _record_module_menu_allowed(module, identity, {"menu_keys": identity.get("menu_keys") or []}):
            commands.append({"id": command_id, "label": label, "prompt": prompt, "skill_id": skill_id, "icon": icon})
    return commands
