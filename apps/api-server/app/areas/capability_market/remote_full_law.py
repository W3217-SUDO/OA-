"""北大法宝“整部法律取全文”（陶威 11-01 同意 A2）：确认一次，自动逐条取完，保存为 Word。

法宝没有一次返回整部法规的工具，只能用 get_law_item_content 按条取。确认卡先写明最多调用几次、
每次多少积分；执行时在同一个会话里并发逐条取，连续取不到 3 条就认为到了末尾，上限 300 条。
"""
import asyncio

from fastapi import HTTPException

from app.agent_mcp.artifacts import _generated_metadata, resource_metadata
from app.core.generated_file_storage import safe_original_name, save_generated_file

FULL_LAW_TOOL = 'get_law_item_content'
PRICE_TOOL = 'list_entitlements'
PRICE_SERVICE = '精准查找法条'
MAX_ARTICLES = 300
EXTRA_CALLS = 3  # 估计条数之外多取几次，用来确认已经到了末尾
STOP_AFTER_EMPTY = 3
CONCURRENCY = 8
BATCH_TIMEOUT_SECONDS = 100  # 留在网关 120 秒以内


def planned_calls(estimated_articles):
    if isinstance(estimated_articles, bool) or not isinstance(estimated_articles, int) or estimated_articles < 1:
        raise HTTPException(422, '请给出这部法律大约有多少条（1 到 300 之间的整数）')
    return min(MAX_ARTICLES, estimated_articles + EXTRA_CALLS)


async def points_per_call(server):
    """开始前查一次单价（积分账户查询，不涉及法规数据）；查不到时确认卡写“以法宝控制台为准”。"""
    from .remote_session import remote_session

    try:
        async with asyncio.timeout(12):
            async with remote_session(server) as (session, _):
                result = await session.call_tool(PRICE_TOOL, arguments={'keyword': PRICE_SERVICE})
    except Exception:
        return None
    items = ((result.structured_content or {}).get('items') or []) if not result.is_error else []
    for item in items:
        if isinstance(item, dict) and PRICE_SERVICE in str(item.get('title', '')) and isinstance(item.get('pointsPerCall'), int):
            return item['pointsPerCall']
    return None


def plan_summary(law_title, calls, price):
    cost = f'每次 {price} 积分，最多约 {calls * price} 积分' if price else '每次积分以北大法宝控制台为准'
    return (f'从北大法宝逐条取《{law_title}》全文：最多调用 {calls} 次（取到最后一条后自动停止），{cost}；'
            '取完保存为 Word 到当前工作区')


def _article(result):
    if result.is_error:
        raise HTTPException(502, '北大法宝返回取条文失败，已停止；已取到的部分没有保存，请稍后重试')
    data = result.structured_content or {}
    content = data.get('content')
    if not isinstance(content, str) or not content.strip():
        return None
    return {'label': data.get('articleLabel') or '', 'content': content.strip(), 'law_title': data.get('lawTitle') or '',
            'document_no': data.get('documentNo') or '', 'timeliness': data.get('timeliness') or '',
            'implement_date': data.get('implementDate') or '',
            'url': ((data.get('citation') or {}).get('url') or '').split('#')[0]}


async def fetch_articles(session, law_title, max_calls):
    articles, calls, empty_run, number = [], 0, 0, 1
    while number <= max_calls and empty_run < STOP_AFTER_EMPTY:
        batch = list(range(number, min(max_calls, number + CONCURRENCY - 1) + 1))
        results = await asyncio.gather(*(session.call_tool(FULL_LAW_TOOL, arguments={'lawTitle': law_title, 'articleNumber': str(n)})
                                         for n in batch))
        calls += len(batch)
        for result in results:
            article = _article(result)
            if article is None:
                empty_run += 1
                if empty_run >= STOP_AFTER_EMPTY:
                    break
                continue
            empty_run = 0
            articles.append(article)
        number = batch[-1] + 1
    if not articles:
        raise HTTPException(404, f'北大法宝没有找到《{law_title}》的条文，请核对法律名称（可先检索法规标题）')
    return articles, calls, empty_run >= STOP_AFTER_EMPTY


def law_markdown(articles, complete):
    first = articles[0]
    title = first['law_title']
    lines = [f'# {title}', '']
    meta = [value for value in (first['document_no'], first['timeliness'],
                                first['implement_date'] and '施行日期：' + first['implement_date']) if value]
    if meta:
        lines += ['　'.join(meta), '']
    lines += [article['content'] for article in articles]
    lines += ['', '来源：北大法宝' + (f'（{first["url"]}）' if first['url'] else '') + '。条号带“之一”等的条文未包含，引用前请核对原文。']
    if not complete:
        lines.append(f'注意：已取到上限 {len(articles)} 条，可能还有后续条文没有取到。')
    return title, '\n\n'.join(lines)


async def save_full_law(articles, complete, identity, db, *, conversation_id, action_id):
    from app.areas.personal_agent import conversations
    from app.areas.personal_agent.project_workspaces import require_workspace_access, state_workspace
    from app.areas.personal_agent.service import _user_dir
    from app.core.constants import WORD_DOCUMENT_CONTENT_TYPE
    from app.core.storage import _docx_bytes

    title, markdown = law_markdown(articles, complete)
    state = await conversations.get_conversation_state(_user_dir(identity['username']), conversation_id)
    case_record = await require_workspace_access(state_workspace(state), identity, db)
    saved = await save_generated_file(
        db, identity, name=safe_original_name(f'{title}（全文）.docx'), content=_docx_bytes(title, markdown),
        content_type=WORD_DOCUMENT_CONTENT_TYPE, source_kind='mcp_generated',
        conversation_id=conversation_id, source_request_id=action_id, case_record=case_record,
    )
    return title, resource_metadata(_generated_metadata(saved['file']))
