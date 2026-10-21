"""通过原 OA 路由读取数据，复用账号、字段、行及案件来源鉴权。"""

from copy import deepcopy
import json

from fastapi import HTTPException

from app.agent_mcp.auth import get_auth_context
from app.agent_mcp.catalog import get_catalog
from app.agent_mcp.service import call_tool
from app.config import settings

MAX_ROWS = 5000
MAX_BYTES = 8 * 1024 * 1024


def eligible(spec):
    return (not spec.is_write and not spec.is_binary_response
            and spec.path != settings.api_prefix + "/data-query"
            and not spec.path.startswith(settings.api_prefix + "/data-query/"))


def field_value(item, path):
    for key in path.split(".") if path else []:
        if not isinstance(item, dict) or key not in item:
            return None
        item = item[key]
    return item


async def read_rows(body):
    spec = get_catalog(get_auth_context().application).get(body.source_tool)
    if not eligible(spec):
        raise HTTPException(422, "数据源必须是已登记的只读 JSON 业务接口，不能使用写接口、文件接口或递归查询")
    rows, total, received, pages = [], None, 0, 0
    for page in range(1, 51 if body.all_pages else 2):
        arguments = deepcopy(body.arguments)
        if body.pagination:
            paging = body.pagination
            container = arguments.setdefault(paging.location, {})
            if not isinstance(container, dict):
                raise HTTPException(422, "原接口分页参数必须是对象")
            container[paging.page_field] = page
            container[paging.size_field] = paging.page_size
        # call_tool 重校验原 schema、登录身份、案件上下文和原路由权限；绝不以服务账号代查。
        result = await call_tool(spec.name, arguments)
        received += len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        if received > MAX_BYTES:
            raise HTTPException(413, "源接口返回超过8MB，请缩小筛选范围或使用原生统计接口")
        batch = field_value(result, body.rows_path)
        if not isinstance(batch, list) or any(not isinstance(item, dict) for item in batch):
            raise HTTPException(422, "rows_path 未指向原接口的对象数组，请按真实响应字段指定")
        pages += 1
        rows.extend(batch)
        if len(rows) > MAX_ROWS:
            raise HTTPException(413, "组合查询最多处理5000条，请缩小原接口筛选范围或使用原生统计接口")
        current_total = field_value(result, body.pagination.total_path if body.pagination else "total")
        if body.all_pages:
            if type(current_total) is not int or current_total < 0:
                raise HTTPException(422, "全量查询需要原接口返回准确的整数总数")
            if current_total > MAX_ROWS:
                raise HTTPException(413, "匹配记录超过5000条，未返回抽样统计，请缩小原接口范围或使用原生统计接口")
            if total is not None and total != current_total:
                raise HTTPException(409, "查询期间源数据总数变化，未返回不完整的全量统计")
            total = current_total
            if len(rows) == total:
                break
            if len(rows) > total or len(batch) != body.pagination.page_size:
                raise HTTPException(409, "源接口分页与总数不一致，未返回不完整统计")
        else:
            total = current_total if type(current_total) is int else None
            break
    else:
        raise HTTPException(413, "原接口分页超过50页，请缩小范围或使用原生统计接口")
    if body.all_pages and rows and all("id" in row for row in rows):
        keys = [json.dumps(row["id"], sort_keys=True) for row in rows]
        if len(set(keys)) != len(keys):
            raise HTTPException(409, "源分页包含重复编号，未返回重复计数的全量统计")
    return rows, {"source_tool": spec.name, "source_total": total, "source_rows": len(rows),
                  "source_pages": pages, "aggregation_scope": "all_matching_source_rows" if body.all_pages else "returned_source_rows",
                  "notice": "已通过原接口获取全部匹配记录；多页读取不代表数据库事务快照。" if body.all_pages else
                  "筛选和统计仅针对本次原接口返回的数据，不能视为全部匹配记录。"}
