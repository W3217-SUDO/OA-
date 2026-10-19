"""通过 DPH 官方 MCP 插件加载 Engram，每人每工作区使用独立数据库。"""
from pathlib import Path

from fastapi import HTTPException

from app.config import settings
from .paths import native_path

TOOLS = ('mem_save', 'mem_search', 'mem_context', 'mem_get_observation',
         'mem_update', 'mem_delete', 'mem_stats')
INSTRUCTION = ('长期记忆使用 engram 工具，按当前登录人及工作区隔离。用户明确要求记住时调用 mem_save，'
               'project 参数留空，沿用当前工作区；只使用已注册的记忆工具。'
               '历史信息相关时先调用 mem_search，需要完整记录再调用 mem_get_observation。'
               '只在工具成功后确认已记住；记忆不是最新业务事实，权限、金额、状态仍须查询 OA。'
               '不得保存密钥、认证请求头、密码或整段原始聊天；用户要求遗忘时检索后删除准确记录。')


def configuration(cwd: Path, owner: str):
    command = settings.deepseek_harness_memory_command.strip()
    if not command:
        return None
    from app.areas.personal_agent.service import _user_dir
    from app.areas.personal_agent.memory_store import list_memories

    if not list_memories(_user_dir(owner), 0)['settings'].get('enabled', True):
        return None
    executable = Path(command).expanduser()
    if not executable.is_absolute() or not executable.is_file():
        raise HTTPException(503, '已启用的 DPH 长期记忆程序不存在，请核对运行配置')
    directory = cwd / '.oa-memory'
    if directory.is_symlink():
        raise HTTPException(503, '长期记忆目录不能使用符号链接')
    directory.mkdir(mode=0o700, exist_ok=True)
    return {'id': 'oa-memory', 'name': '@deepseek-ai/dsh-mcp-client', 'config': {
        'serverName': 'engram', 'transport': 'stdio', 'command': native_path(executable),
        'args': ['mcp', '--tools=' + ','.join(TOOLS)],
        'cwd': native_path(cwd), 'env': {
            'ENGRAM_DATA_DIR': native_path(directory), 'ENGRAM_CLOUD_AUTOSYNC': '0',
            'ENGRAM_CLOUD_SERVER': '', 'ENGRAM_CLOUD_TOKEN': '',
        }, 'failOnStartupError': True, 'reconnect': {'enabled': False}}}
