"""确认卡片的中文显示名：参数名和代码值都转成中文，不把内部代码名给用户看（501137）。

只用于显示；执行仍用原参数。显示名随预览一起保存，历史确认记录按保存时的名称显示。
"""

import re

OTHER_FIELD = "其他信息"

# 代码值的中文：按参数名区分，同一个代码在不同参数里含义可能不同。
VALUE_LABELS = {
    "action": {
        "accept": "接受任务", "reject": "拒绝任务", "handoff": "转交任务", "complete": "完成任务",
        "confirm": "发起人确认完成", "restart": "重启任务", "feedback": "任务沟通留言",
        "withdraw": "撤回", "rollback": "回滚", "resend": "重新发送", "start": "开始处理", "assign": "指派",
    },
    "finance_scope": {"firm": "财务中心（律所）", "platform": "平台财务中心", "internal": "内部"},
    "level": {"first": "一审", "second": "二审", "retrial": "再审"},
    "scope": {"mine": "我的", "company": "公司", "department": "部门", "dept": "部门", "pending": "待处理"},
    "decision": {"approve": "确认", "reject": "取消"},
}

_CUT = re.compile(r"[（(，,；;：:=。]")
_HAS_CHINESE = re.compile(r"[一-鿿]")


def has_chinese(text: str) -> bool:
    return bool(_HAS_CHINESE.search(str(text or "")))


def _schema_label(schema: dict) -> str:
    """业务工具参数说明的第一段就是中文名，如“任务 ID（见 biz_my_tasks）”取“任务 ID”。"""
    text = str(schema.get("description") or "").strip()
    head = _CUT.split(text, 1)[0].strip()
    if head and has_chinese(head) and len(head) <= 16 and not head.isascii():
        return head
    return ""


def field_label(name: str, labels: dict | None = None) -> str:
    from app.agent_mcp.action_summary import _FIELD_LABELS
    if labels and labels.get(name):
        return labels[name]
    if name in _FIELD_LABELS:
        return _FIELD_LABELS[name]
    return name if has_chinese(name) else OTHER_FIELD


def value_label(name: str, value, values: dict | None = None):
    mapping = (values or {}).get(name) or VALUE_LABELS.get(name) or {}
    if isinstance(value, str) and value in mapping:
        return mapping[value]
    return value


def labels_from_schema(properties: dict, prefix: str = "") -> tuple[dict, dict]:
    """从业务工具的参数定义取中文名和枚举值的中文（嵌套对象按“上级.下级”记）。"""
    fields: dict[str, str] = {}
    values: dict[str, dict] = {}
    for name, schema in (properties or {}).items():
        if not isinstance(schema, dict):
            continue
        key = prefix + name
        label = _schema_label(schema)
        if label:
            fields[key] = label
            fields.setdefault(name, label)
        enum = schema.get("enum")
        if isinstance(enum, list):
            known = {**VALUE_LABELS.get(name, {})}
            for item in enum:
                if isinstance(item, str) and item not in known and has_chinese(item):
                    known[item] = item
            if known:
                values[name] = known
        if schema.get("type") == "object" and isinstance(schema.get("properties"), dict):
            nested_fields, nested_values = labels_from_schema(schema["properties"], key + ".")
            fields.update({k: v for k, v in nested_fields.items() if k not in fields})
            values.update({k: v for k, v in nested_values.items() if k not in values})
        items = schema.get("items")
        if isinstance(items, dict) and isinstance(items.get("properties"), dict):
            nested_fields, nested_values = labels_from_schema(items["properties"], key + ".")
            fields.update({k: v for k, v in nested_fields.items() if k not in fields})
            values.update({k: v for k, v in nested_values.items() if k not in values})
    return fields, values


def display_maps(values_by_group: dict, schema_properties: dict | None = None) -> dict:
    """给预览准备 field_labels / value_labels：业务工具参数说明优先，其次常用字段表，最后“其他信息”。"""
    fields, values = labels_from_schema(schema_properties or {})

    def walk(value, prefix=""):
        if isinstance(value, dict):
            for name, item in value.items():
                fields.setdefault(name, field_label(name, fields))
                if name in VALUE_LABELS and name not in values:
                    values[name] = VALUE_LABELS[name]
                walk(item, prefix + name + ".")
        elif isinstance(value, list):
            for item in value:
                walk(item, prefix)

    walk(values_by_group)
    return {"field_labels": fields, "value_labels": values}
