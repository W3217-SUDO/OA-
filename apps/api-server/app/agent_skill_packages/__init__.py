"""随系统发布的完整智能体技能包（指令、参考资料和可在隔离沙箱运行的脚本）。

技能目录随运行包一起发布，不从外部下载；运行时按内容摘要存成与 GitHub 安装相同的技能快照，
脚本仍只能经隔离运行服务执行。
"""

from functools import lru_cache
import hashlib
from importlib import import_module
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGES = {"court-doc-intake": "court_doc_intake"}


def package_files(skill_id: str) -> dict[str, bytes]:
    """技能快照内容：文档来自包内 documents.py（运行包只发 Python 文件），脚本取 scripts/ 下的源码。"""
    module = PACKAGES[skill_id]
    files = {name: text.encode("utf-8") for name, text in import_module(f"{__name__}.{module}.documents").DOCUMENTS.items()}
    scripts = ROOT / module / "scripts"
    files.update({f"scripts/{path.name}": path.read_bytes() for path in sorted(scripts.glob("*.py")) if path.name != "__init__.py"})
    return files


def instruction(skill_id: str) -> str:
    """SKILL.md 去掉元数据后的正文。"""
    text = package_files(skill_id)["SKILL.md"].decode("utf-8").replace("\r\n", "\n")
    if text.startswith("---\n"):
        text = text.split("\n---\n", 1)[1]
    return text.strip()


@lru_cache(maxsize=None)
def manifest(skill_id: str) -> dict:
    """只计算摘要清单（用于目录展示），不写文件。"""
    files = {path: hashlib.sha256(data).hexdigest() for path, data in sorted(package_files(skill_id).items())}
    return {"id": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(), "files": files}


@lru_cache(maxsize=None)
def bundle(skill_id: str) -> dict:
    """保存为内容寻址的技能快照，供原生技能目录发布和隔离脚本执行。"""
    from app.harness_agent.bundles import store_files
    return store_files(package_files(skill_id))
