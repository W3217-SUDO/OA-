"""将远程 MCP 内嵌文件保存到原会话空间，聊天只保留受控文件引用。"""
import base64
import binascii
import json
import mimetypes

from fastapi import HTTPException

from app.agent_mcp.artifacts import _generated_metadata, resource_metadata
from app.agent_mcp.auth import get_auth_context
from app.core.generated_file_storage import MAX_GENERATED_BYTES, safe_original_name, save_generated_file


MAX_REMOTE_RESULT_BYTES = ((MAX_GENERATED_BYTES + 2) // 3) * 4 + 65536


async def store_remote_files(result, configuration, identity, db, *, tool_name, conversation_id, action_id):
    from app.areas.personal_agent import conversations
    from app.areas.personal_agent.project_workspaces import require_workspace_access, state_workspace
    from app.areas.personal_agent.service import _user_dir
    from .remote_tools import safe_remote

    files = []
    total = 0
    credentials = [get_auth_context().bearer]
    for server in configuration['mcp.json']['mcpServers'].values():
        for value in server.get('headers', {}).values():
            credentials.append(value)
            if value.lower().startswith('bearer '):
                credentials.append(value[7:])

    def project(value, path=(), depth=0):
        nonlocal total
        if depth > 64:
            raise HTTPException(502, '外部MCP结果嵌套层数超过限制')
        if isinstance(value, list):
            return [project(child, (*path, index), depth + 1) for index, child in enumerate(value)]
        if not isinstance(value, dict):
            return value
        if 'blob' not in value or 'uri' not in value:
            return {key: project(child, (*path, key), depth + 1) for key, child in value.items()}
        encoded, mime = value['blob'], value.get('mimeType')
        if not isinstance(encoded, str) or len(encoded) > MAX_REMOTE_RESULT_BYTES:
            raise HTTPException(413, '外部MCP文件超过20MB限制或编码无效')
        if not isinstance(mime, str) or not mime or len(mime) > 128:
            raise HTTPException(502, '外部MCP文件缺少有效的媒体类型')
        extension = mimetypes.guess_extension(mime, strict=False)
        if extension is None:
            raise HTTPException(502, '外部MCP文件媒体类型无法确定文件扩展名')
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(502, '外部MCP文件不是有效的Base64内容') from exc
        total += len(content)
        if not content or total > MAX_GENERATED_BYTES or len(files) >= 8:
            raise HTTPException(413, '外部MCP文件为空、超过8个或合计超过20MB')
        if mime == 'application/pdf' and not content.startswith(b'%PDF-'):
            raise HTTPException(502, '外部MCP声明的PDF文件内容无效')
        if any(secret and len(secret) >= 8 and secret.encode() in content for secret in credentials):
            raise HTTPException(502, '外部MCP文件包含连接凭据回声，已阻断保存')
        name = safe_original_name(f'{tool_name}-{len(files) + 1}{extension}')
        # 保存结构路径，不根据外部 URI 识别本地引用；全部检查通过后才开始持久保存。
        files.append((path, name, mime, content))
        return {'type': 'resource_link', 'name': name}

    value = safe_remote(project(result.model_dump(mode='json', by_alias=True)), configuration)
    if len(json.dumps(value, ensure_ascii=False).encode()) > 65536:
        raise HTTPException(502, '外部MCP非文件结果超过64KB限制；请核对实际状态，禁止重复提交')
    if not files:
        return value
    if len(json.dumps(value, ensure_ascii=False).encode()) + len(files) * 2048 > 65536:
        raise HTTPException(502, '外部MCP文件引用与元数据合计超过64KB限制，未开始保存')
    for path, _, _, _ in files:
        parent = value
        for key in path[:-1]:
            if (isinstance(parent, dict) and key not in parent) or not isinstance(parent, (dict, list)):
                raise HTTPException(502, '外部MCP文件位于敏感字段，已阻断保存')
            parent = parent[key]
        if not path or (isinstance(parent, dict) and path[-1] not in parent):
            raise HTTPException(502, '外部MCP文件引用结构无效')
    state = await conversations.get_conversation_state(_user_dir(identity['username']), conversation_id)
    workspace = state_workspace(state)
    case_record = await require_workspace_access(workspace, identity, db)
    references = []
    for path, name, mime, content in files:
        saved = await save_generated_file(
            db, identity, name=name, content=content, content_type=mime, source_kind='mcp_generated',
            conversation_id=conversation_id, source_request_id=action_id, case_record=case_record,
        )
        reference = resource_metadata(_generated_metadata(saved['file']))
        parent = value
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = reference
        references.append(reference)
    value['files'] = references
    return value
