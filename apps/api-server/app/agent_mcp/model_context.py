"""模型专用查询投影；原接口、待确认操作和附件资源保持完整。"""

import json
from typing import Any


TOOL_RESULT_BYTES = 24_000
REQUEST_TEXT_BYTES = 192_000
MODEL_QUERY_RULES = (
    "查询总体数量、阶段分布或整体情况时，优先搜索全量统计接口，例如案件全量统计，"
    "不能把当前页或摘要样本的条数当作总数。查询结果中的 total、summary、totals、"
    "phase_counts 等仅按接口标明的筛选范围解释。"
    "带 _model_projection 或 omitted_items 的数据只展示部分明细；必须说明覆盖范围，"
    "需要具体字段时按原接口分页、缩小筛选范围或读取对应记录详情，不得从样本推算全量汇总。"
)
_PRIORITY = (
    "isError", "detail", "status", "status_code", "request_id", "confirmation_url", "preview",
    "capabilities", "identity", "case", "document_readings", "pending_actions", "result", "total", "TotalItemCount", "summary", "totals",
    "phase_counts", "case_type_counts", "total_amount", "filters", "aggregation_scope",
    "page", "page_size", "pages", "PageNo", "PageSize", "id", "serial_no", "name", "title",
    "customer", "owner", "amount", "created_at", "updated_at",
)
_COMPLETE_FIELDS = {
    "capabilities", "identity", "document_readings", "pending_actions", "preview", "confirmation_url",
    "total", "TotalItemCount", "summary", "totals", "phase_counts", "case_type_counts", "total_amount",
}


def encoded_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8"))


def _protected(value: Any) -> bool:
    return isinstance(value, dict) and (
        value.get("status") == "pending" or value.get("type") == "resource_link"
    )


def _contains_protected_context(value: Any) -> bool:
    if isinstance(value, dict):
        return _protected(value) or any(
            key in {"capabilities", "identity", "document_readings", "pending_actions", "preview", "confirmation_url"}
            or _contains_protected_context(item)
            for key, item in value.items()
        )
    return isinstance(value, list) and any(_contains_protected_context(item) for item in value)


def _checked_projection(value: Any, budget: int) -> Any:
    if encoded_size(value) > budget:
        raise RuntimeError("查询摘要超出模型输入范围，请缩小查询范围")
    return value


def model_result_view(value: Any, budget: int = TOOL_RESULT_BYTES) -> Any:
    if encoded_size(value) <= budget:
        return value
    if _protected(value):
        raise RuntimeError("待确认操作或附件链接超出模型输入范围，请在原业务页面核对完整内容")
    if isinstance(value, dict):
        projected = {}
        omitted = []
        ordered = [key for key in _PRIORITY if key in value]
        ordered.extend(key for key in value if key not in ordered)
        # 为省略说明预留空间，保持合法 JSON，而非截断序列化文本。
        remaining = budget - 1_200
        for key in ordered:
            item = value[key]
            if key in _COMPLETE_FIELDS or _protected(item):
                size = encoded_size({key: item})
                if size > remaining:
                    raise RuntimeError("身份权限、待确认操作或附件链接过长，请缩小本轮查询范围")
                selected = item
            elif remaining < 600:
                omitted.append(str(key))
                continue
            else:
                selected = model_result_view(item, remaining)
                size = encoded_size({key: selected})
            if size > remaining:
                omitted.append(str(key))
                continue
            projected[key] = selected
            remaining -= size
        projected["_model_projection"] = {
            "omitted_fields": [name[:32] for name in omitted[:8]], "omitted_field_count": len(omitted),
            "notice": "仅为模型提供查询摘要；省略字段须读取详情，不能视为空值或据此作全量统计。",
        }
        return _checked_projection(projected, budget)
    if isinstance(value, list):
        included = []
        remaining = budget - 600
        for item in value:
            if remaining < 600:
                break
            selected = model_result_view(item, min(remaining, 2_400))
            size = encoded_size(selected) + 1
            if size > remaining:
                break
            included.append(selected)
            remaining -= size
        return _checked_projection({
            "items": included, "returned_items": len(value), "included_items": len(included),
            "omitted_items": len(value) - len(included),
            "notice": "这是原查询返回页的部分明细，不是全部记录；全量统计以原接口汇总为准，明细请分页或读取详情。",
        }, budget)
    if isinstance(value, str):
        projected = {
            "text_preview": "", "original_characters": len(value),
            "omitted_characters": len(value),
            "notice": "此字段仅为文字预览；未展示内容不能声称已读取。",
        }
        # 按最终 JSON 字节计算预算，引号和反斜杠转义也占用空间。
        low, high = 0, len(value)
        while low < high:
            middle = (low + high + 1) // 2
            projected["text_preview"] = value[:middle]
            projected["omitted_characters"] = len(value) - middle
            if encoded_size(projected) <= budget:
                low = middle
            else:
                high = middle - 1
        projected["text_preview"] = value[:low]
        projected["omitted_characters"] = len(value) - low
        return _checked_projection(projected, budget)
    raise RuntimeError("查询字段超出模型输入范围，请缩小查询范围")


def discovered_tools_view(tools: list[dict]) -> dict:
    visible = []
    for tool in tools:
        candidate = {"tools": [*visible, tool]}
        if encoded_size(candidate) > TOOL_RESULT_BYTES - 600:
            continue
        visible.append(tool)
    if tools and not visible:
        raise RuntimeError("工具参数定义过长，请使用原业务页面，不会截断参数定义后调用")
    return {
        "tools": visible, "omitted_tools": len(tools) - len(visible),
        "notice": "仅这些工具的参数定义完整可用；未展示候选请缩小搜索词后重新发现。",
    }


def _text_size(payload: dict) -> int:
    # 图片保持原样发送；base64 字节不是文本 token，不参与文字预算。
    messages = []
    for message in payload.get("messages", []):
        content = message.get("content")
        if isinstance(content, list):
            content = [item if item.get("type") != "image_url" else {"type": "image_url"} for item in content]
        messages.append({**message, "content": content})
    return encoded_size({**payload, "messages": messages})


def bounded_model_payload(payload: dict) -> dict:
    if _text_size(payload) <= REQUEST_TEXT_BYTES:
        return payload
    messages = [dict(message) for message in payload["messages"]]
    bounded = {**payload, "messages": messages}
    # 保留消息顺序、tool_calls 参数及全部对应回复，只压缩较早的只读查询结果。
    for message in messages:
        if message.get("role") != "tool":
            continue
        value = json.loads(message["content"])
        if _contains_protected_context(value):
            continue
        if isinstance(value, dict) and isinstance(value.get("tools"), list):
            # 旧目录可重新搜索，但不能把残缺 schema 当成可调用参数定义。
            value = {
                "previous_tool_names": [tool["name"] for tool in value["tools"]],
                "notice": "较早工具定义已移出模型上下文；调用前必须重新搜索并读取完整 schema。",
            }
        message["content"] = json.dumps(model_result_view(value, 4_000), ensure_ascii=False, default=str)
        if _text_size(bounded) <= REQUEST_TEXT_BYTES:
            return bounded
    raise RuntimeError("本轮资料超过模型输入范围，请缩小查询范围、分批处理附件或开启新的会话")
