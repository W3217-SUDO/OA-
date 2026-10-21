"""面向登录用户和智能体的灵活只读查询接口，只组合原有授权接口。"""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agent_mcp.auth import get_auth_context
from app.agent_mcp.catalog import get_catalog
from app.config import settings
from app.security import current_identity

from .models import DataQuery
from .source import eligible, read_rows
from .transform import transform

router = APIRouter(prefix=settings.api_prefix + "/data-query", tags=["组合数据查询"])


@router.get("/sources", summary="发现组合查询数据源及原接口参数")
async def list_data_query_sources(query: str = Query(min_length=1, max_length=100),
                                  _identity=Depends(current_identity)):
    catalog = get_catalog(get_auth_context().application)
    found = [spec for spec in catalog.tools if eligible(spec)
             and query.casefold() in (spec.name + " " + spec.title + " " + spec.description).casefold()]
    return {"items": [{"name": spec.name, "title": spec.title, "path": spec.path,
                       "input_schema": spec.input_schema} for spec in found[:20]],
            "total": len(found), "notice": "目录不是数据授权，执行时仍由原接口逐次校验账号权限。"}


@router.post("", summary="组合筛选、字段选择、排序分页及分组统计（只读）")
async def query_interface_data(body: DataQuery, _identity=Depends(current_identity)):
    """先通过 sources 或 OA 工具发现读取原接口 schema。source_tool/arguments 使用该接口的准确名称与参数；rows_path 指向对象数组，空字符串表示响应本身是数组。支持 AND/OR 筛选、字段投影、分组及 count/sum/avg/min/max；数字统计按十进制字符串返回。默认仅处理源接口本次返回的数据；需要全量时显式指定 all_pages 和原接口 pagination，超过5000条拒绝抽样统计。不能提交 SQL、指定账号、查询写接口或绕过原有字段与数据权限。"""
    try:
        async with asyncio.timeout(45):
            if len(body.model_dump_json().encode("utf-8")) > 256 * 1024:
                raise HTTPException(413, "查询参数超过256KB，请缩小参数范围")
            rows, scope = await read_rows(body)
            result = {**transform(rows, body), **scope}
            if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 1024 * 1024:
                raise HTTPException(413, "结果超过1MB，请选择更少字段或降低返回条数")
            return result
    except TimeoutError as exc:
        raise HTTPException(504, "组合查询超过45秒，未返回不完整统计") from exc
